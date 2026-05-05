# ADR-005: measurements 파티셔닝 — 현재 단일 테이블, 운영 시 월별 RANGE 파티셔닝

**상태**: Accepted  
**날짜**: 2026-05-05

---

## 컨텍스트

`measurements` 테이블은 Lot당 약 1,250만 행이 발생한다.
누적 시 수억 행에 도달하면 단일 테이블 인덱스 자체가 무거워져 조회 성능이 저하된다.
동시에 오래된 측정 데이터의 정기 삭제 비용도 커진다.

PostgreSQL의 시간 기반 RANGE 파티셔닝이 이 문제를 해결하지만,
파티셔닝 설정·자동화·검증에 1~2일이 소요된다.

## 결정

**현재**: 단일 테이블 + 인덱스 4종으로 구현한다.
**운영 시**: `created_at` 기준 **월별 RANGE 파티셔닝**으로 전환한다.

### 현재 인덱스 (단일 테이블)
```sql
-- 시나리오 6: 특정 part의 모든 측정값 조회
CREATE INDEX idx_measurements_part_test ON measurements (part_id, test_id);

-- 수율 분석: 합격/불합격 필터
CREATE INDEX idx_measurements_part_pass ON measurements (part_id, is_pass);

-- 시계열 범위 조회
CREATE INDEX idx_measurements_test_time ON measurements (test_id, created_at);

-- 알람 발생 추적 (전체의 ~0.1% → 부분 인덱스)
CREATE INDEX idx_measurements_alarm ON measurements (is_alarm) WHERE is_alarm = TRUE;
```

### 운영 시 전환 DDL (참고)
```sql
CREATE TABLE measurements (
    id          BIGINT NOT NULL,
    part_id     BIGINT NOT NULL,
    test_id     BIGINT NOT NULL,
    result      DOUBLE PRECISION,
    is_pass     BOOLEAN NOT NULL,
    is_alarm    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (id, created_at)   -- 파티션 키 포함 필수
) PARTITION BY RANGE (created_at);

CREATE TABLE measurements_2026_05 PARTITION OF measurements
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

## 결과

### 긍정적 (현재 단일 테이블)
- 구현 단순, 검증 빠름
- 데모 규모(수만 행)에서 성능 충분
- 파티셔닝 가능 구조로 컬럼을 설계해뒀으므로 (`created_at` 보유) 미래 전환 비용 최소

### 긍정적 (운영 시 파티셔닝)
- 시간 범위 쿼리 시 해당 파티션만 스캔 (Partition Pruning)
- 오래된 파티션 `DROP TABLE measurements_YYYY_MM` 으로 즉시 삭제
- 파티션별 인덱스가 작아져 유지 비용 감소

### 부정적 / 트레이드오프
- 파티션 키가 없는 쿼리는 모든 파티션 스캔 — 반드시 `created_at` 조건을 포함해야 함
- PK가 `(id, created_at)` 복합으로 강제됨 — ORM 매핑 시 주의 필요
- 파티션을 가로지르는 UNIQUE 제약·FK 설정이 까다로움

### 전환 트리거 기준
- 단일 테이블 행 수가 **1억 행** 초과 시 파티셔닝 도입 검토
- `EXPLAIN ANALYZE` 결과에서 Seq Scan이 반복 등장 시 즉시 도입
