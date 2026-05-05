# Chip Test Data Platform

팹리스 회사가 외주 ATE(Automatic Test Equipment)에서 받는 STDF 파일을 자동으로 수집·파싱·저장하고,
엔지니어가 안전하게 분석할 수 있도록 데이터를 제공하는 백엔드 플랫폼.

## 핵심 기능

- **STDF 파일 자동 수집** — OSAT가 HTTP API로 파일 업로드 → 202 즉시 응답 → RabbitMQ 비동기 처리
- **실시간 처리 상태 알림** — Redis Pub/Sub + SSE로 파싱 완료·FAIL률 초과 이벤트 즉시 전달
- **데이터 조회 API** — Lot·Wafer·Part·측정값 조회, 인덱스 최적화로 수억 행 대응 설계
- **RBAC + Audit Log** — Engineer / Lead / Admin 역할 분리, 모든 행위 추적

## 기술 스택

| 분야 | 기술 |
|---|---|
| 백엔드 프레임워크 | FastAPI + uvicorn (async) |
| DB / ORM | PostgreSQL 16 + SQLAlchemy 2.0 + Alembic |
| 메시지 큐 | RabbitMQ 3.13 + aio-pika |
| 캐시 / 실시간 | Redis 7 (Cache-Aside + Pub/Sub) |
| 인증 | JWT (pyjwt) + bcrypt |
| STDF 파서 | pystdf |
| 의존성 관리 | uv |
| 컨테이너 | Docker Compose |
| 프론트엔드 | Vite + React + TypeScript + Tailwind CSS |

## 시작하기

### 사전 요구사항

- Docker Desktop
- Python 3.12+
- uv (`brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 실행

```bash
# 1. 환경 변수 설정
cp backend/.env.example backend/.env

# 2. 전체 스택 기동
docker compose up -d

# 3. DB 마이그레이션
cd backend && alembic upgrade head

# 4. API 문서 확인
open http://localhost/api/docs
```

### 로컬 개발 (백엔드)

```bash
cd backend
uv sync
.venv/bin/uvicorn app.main:app --reload --port 8000
```

## 프로젝트 구조

```
chip-test-data-platform/
├── backend/
│   ├── app/
│   │   ├── core/          # 설정, JWT/bcrypt
│   │   ├── db/            # AsyncSession
│   │   ├── models/        # SQLAlchemy 모델 (13개 테이블)
│   │   ├── schemas/       # Pydantic 스키마
│   │   ├── routers/       # FastAPI 라우터
│   │   ├── services/      # 비즈니스 로직
│   │   └── storage/       # 파일 스토리지 추상화
│   ├── alembic/           # DB 마이그레이션
│   ├── docs/adr/          # 기술 의사결정 기록 (ADR 001~007)
│   └── tests/
├── frontend/              # Vite + React + TypeScript
├── nginx/                 # 리버스 프록시
└── docker-compose.yml
```

## 시스템 아키텍처

```
[OSAT]──POST /api/v1/stdf-files──▶[Nginx]──▶[FastAPI]──▶[RabbitMQ]
                                                │                │
                                           [Redis]         [Worker]
                                           Cache+Pub/Sub    pystdf 파싱
                                                │                │
                                           [SSE /events]  [PostgreSQL]
                                                │
                                          [Frontend]
```

## API 엔드포인트

전체 명세는 `docker compose up` 후 **http://localhost/api/docs** (Swagger UI) 에서 확인.

| 엔드포인트 | 설명 |
|---|---|
| `POST /api/v1/auth/register` | 회원가입 |
| `POST /api/v1/auth/login` | 로그인 (JWT 발급) |
| `POST /api/v1/stdf-files` | STDF 파일 업로드 (202 비동기) |
| `GET  /api/v1/lots` | Lot 목록 조회 |
| `GET  /api/v1/lots/{id}` | Lot 상세 + 수율 통계 |
| `GET  /api/v1/measurements` | 측정값 조회 (part_id 필수) |
| `GET  /api/v1/events` | 실시간 이벤트 스트림 (SSE) |
| `GET  /api/v1/audit-logs` | 감사 로그 (Admin 전용) |

## 핵심 설계 결정

설계 근거는 [`backend/docs/adr/`](backend/docs/adr/) 참조.

- **RabbitMQ 비동기 처리** (ADR-001) — STDF 파일 수신과 파싱을 분리, 202 즉시 응답
- **PostgreSQL + 완전 정규화** (ADR-002) — 수억 행 측정값 분석 쿼리 최적화
- **단일 코드베이스 / 별도 프로세스** (ADR-003) — API·Worker 독립 확장
- **Redis Pub/Sub** (ADR-007) — STDF 파싱 완료·FAIL률 초과 실시간 알림

## 데이터 모델

13개 테이블 — 권한(roles, permissions, users), 도메인(osats, lots, wafers, parts, tests, measurements, stdf_files, file_processing_jobs), 감사(audit_logs).

ERD 및 인덱스 설계: [Phase 1.1 설계 문서](https://www.notion.so/355134272658806f824fe957bce7477d)

## 향후 계획

- [ ] S3 스토리지 백엔드 (`backend/app/storage/s3.py`)
- [ ] measurements 월별 Range 파티셔닝 (1억 행 도달 시)
- [ ] Prometheus + Grafana 모니터링
- [ ] CI/CD (GitHub Actions)
