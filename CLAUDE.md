# Chip Test Data Platform — Claude Code 작업 규칙

## 프로젝트 개요

- **목표**: 퀄리타스반도체 신입 백엔드 개발자 채용 포트폴리오
- **주제**: 칩 검증 데이터 관리 시스템 (Chip Test Data Platform)
- **마감**: 2026-05-10
- **구현 시나리오**: 1 (STDF 업로드), 3 (Lot 분석), 6 (측정값 조회) 3가지만

## 노션 워크스페이스

- **프로젝트 페이지** (공개 가능): https://www.notion.so/syk25/355134272658806f824fe957bce7477d
- **작업 공간** (사적 자료): https://www.notion.so/syk25/35613427265881428f16c3aea7241d58

## 세션 시작 절차 (매 세션 반드시 준수)

1. 작업 공간의 "📊 진행 상황 대시보드" fetch → 현재 진행 상황 확인
2. "🤝 대화 규칙 & 기록 규칙" fetch → 대화 방식 복원
3. 가장 최근 완료된 단계의 결과물 fetch
4. "현재 X 단계 완료, 다음은 Y. 진행할까요?" 형태로 보고
5. 사용자 확인 후에만 진입

## 대화 규칙

- 신입/비전공자 눈높이 설명 (사용자는 화학 전공 비전공자)
- **한 번에 한 단계만** — 단계가 끝나기 전에 다음 단계 진입 금지
- **응원·칭찬·격려 표현 금지** — 정보 전달만
- 결과 나오면 즉시 노션 저장 + 대시보드 업데이트 후 다음 단계 진입

## 기록 위치 규칙

| 결과물 종류 | 저장 위치 |
|---|---|
| 설계 결과물 (ERD, API, 아키텍처, ADR) | 프로젝트 페이지 > 📝 단계별 결과물 (자식 페이지) |
| 진행률·체크리스트·일자별 추적 | 작업 공간 > 📊 진행 상황 대시보드 |
| 기술 개념 학습 노트 | 작업 공간 > 🧠 핵심 개념 학습 노트 |
| 도메인 학습 (ATE, STDF 등) | 작업 공간 > 📚 도메인 학습 노트 |

## 기술 스택

- **의존성 관리**: uv (Astral, Rust 기반)
- **백엔드**: FastAPI + uvicorn + SQLAlchemy 2.0 + Alembic + asyncpg + Pydantic v2
- **인증**: pyjwt + passlib[bcrypt]
- **메시지 큐 클라이언트**: aio-pika (RabbitMQ)
- **캐시 클라이언트**: redis[asyncio]
- **STDF 파서**: pystdf
- **로깅**: structlog
- **설정**: pydantic-settings
- **테스트**: pytest + pytest-asyncio + httpx

## 인프라 (docker-compose.yml)

| 서비스 | 이미지 | 포트 |
|---|---|---|
| db | postgres:16-alpine | 5432 |
| rabbitmq | rabbitmq:3.13-management-alpine | 5672, 15672 |
| redis | redis:7-alpine | 6379 |
| api | 자체 빌드 (Dockerfile) | nginx 경유 |
| worker | 자체 빌드 (공통 이미지) | - |
| nginx | nginx:alpine | 80 |
| frontend | 자체 빌드 (Vite+React) | nginx 경유 |

## 폴더 구조

```
chip-test-data-platform/
├── backend/           # FastAPI 애플리케이션
│   ├── app/
│   │   ├── core/      # config, security
│   │   ├── db/        # session, base
│   │   ├── models/    # SQLAlchemy 모델 (13개 테이블)
│   │   ├── schemas/   # Pydantic 스키마
│   │   ├── routers/   # FastAPI 라우터
│   │   ├── services/  # 비즈니스 로직
│   │   └── storage/   # interface.py + local.py
│   ├── alembic/
│   ├── docs/adr/      # ADR 001~006
│   └── tests/
├── frontend/          # Vite + React + TypeScript
├── nginx/             # nginx.conf
├── docker-compose.yml
├── Dockerfile         # 백엔드용
└── .env.example
```

> **참고**: backend/ 폴더 분리는 프론트엔드 추가와 함께 진행 예정 (현재 루트에 app/ 존재)

## 핵심 설계 결정 (ADR 요약)

- **ADR-001**: RabbitMQ 비동기 처리 — STDF 파일은 완성된 파일 단위로 HTTP 업로드 (스트리밍 아님)
- **ADR-002**: PostgreSQL + measurements 완전 정규화 (lots.raw_mir만 JSONB)
- **ADR-003**: 단일 코드베이스 / api·worker 별도 프로세스 (공통 Dockerfile, command로 분리)
- **ADR-004**: 파일 스토리지 인터페이스 추상화 (로컬 → S3 교체 1줄)
- **ADR-005**: measurements 파티셔닝 보류 (1억 행 도달 시 월별 RANGE)
- **ADR-006**: 모니터링 보류 (structlog 현재, Prometheus/Grafana 운영 시)

## 의사결정 우선순위 (충돌 시)

**시간 > 이해 > 채용공고 요구사항 > 면접 방어 가능성**
