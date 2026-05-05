# ADR-002: PostgreSQL 선택 + measurements 완전 정규화

**상태**: Accepted  
**날짜**: 2026-05-05

---

## 컨텍스트

STDF 파일에서 추출되는 데이터는 크게 두 종류다:
- **메타데이터** (Lot, Wafer 정보): 건수 적고 구조 불확정적 (MIR 필드 30+)
- **측정값** (measurements): Lot당 약 1,250만 행, 집계·필터 쿼리가 핵심 업무

MongoDB 같은 NoSQL 또는 JSONB 하이브리드를 쓰는 경우도 있으나,
분석 쿼리 중심 시스템에서의 적합성을 검토해야 한다.

## 결정

**PostgreSQL**을 메인 DB로 선택하고, 측정값 테이블(`measurements`)은 **완전 정규화**한다.
단, 구조 불확정적인 MIR 메타데이터(`lots.raw_mir`)는 JSONB로 저장한다.

### 테이블 구조 요약
- `measurements(id, part_id, test_id, result, is_pass, is_alarm, created_at)` — 7컬럼
- `tests(id, test_num, name, unit, lo_limit, hi_limit)` — 마스터 테이블 별도 분리
- `lots.raw_mir JSONB` — MIR 원본 통째 저장

### 선택 기준 (JSONB vs 정규화)

| 기준 | lots.raw_mir | measurements |
|---|---|---|
| 데이터 크기 | 소 (수 KB) | 대 (수억 행) |
| 분석 쿼리 비중 | 낮음 | 압도적 |
| 스키마 안정성 | 불안정 (외부 시스템) | 안정 (자체 정의) |
| 필터 패턴 | 드물고 단순 | 자주, 범위·부등호 |

→ 조건이 다르면 선택이 다르다. 모든 것을 JSONB로 채우는 것은 PostgreSQL을 쓰는 이점을 버리는 것.

## 결과

### 긍정적
- `(part_id, test_id)` 복합 인덱스로 시나리오 6(측정값 조회) 쿼리가 인덱스만 탐
- `is_pass`, `is_alarm` 컬럼에 인덱스 → 수율 분석 쿼리 최적화
- `tests` 마스터 테이블 분리로 unit/limit 값 중복 저장 방지
- `is_pass`는 `GENERATED ALWAYS AS (hard_bin = 1) STORED` — DB가 정합성 보장
- PostgreSQL ACID 트랜잭션으로 데이터 무결성 위임

### 부정적 / 트레이드오프
- Lot당 1,250만 행 → 누적 시 수억 행 예상 (파티셔닝 계획 필요, ADR-005 참조)
- 스키마 변경 시 마이그레이션 필요 (Alembic으로 관리)
- 수평 확장은 단일 PostgreSQL보다 샤딩/분산 DB가 유리하나 현 규모에서 불필요

### 보류 / 운영 시점
- `measurements` 월별 RANGE 파티셔닝 (ADR-005)
- `lots.raw_mir` 자주 쿼리되는 키에 표현식 인덱스 추가
- 읽기 부하 집중 시 Read Replica 도입
