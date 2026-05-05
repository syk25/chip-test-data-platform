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

## 빠른 시작

### 사전 요구사항

- Docker Desktop (실행 중 상태)

### 실행

```bash
# 1. 환경 변수 설정
cp backend/.env.example backend/.env

# 2. 전체 스택 빌드 & 기동
docker compose up -d --build

# 3. DB 마이그레이션 (최초 1회)
docker compose exec api alembic upgrade head

# 4. 브라우저에서 접속
open http://localhost          # 프론트엔드 UI
open http://localhost/api/docs # Swagger UI
```

> **기본 계정 생성**
> ```bash
> curl -s -X POST http://localhost/api/v1/auth/register \
>   -H "Content-Type: application/json" \
>   -d '{"email":"engineer@example.com","password":"password123","name":"홍길동"}' | python3 -m json.tool
> ```

### 서비스 구성

| 서비스 | 역할 | 접속 |
|---|---|---|
| nginx | 리버스 프록시 | http://localhost |
| api | FastAPI | http://localhost/api/docs |
| worker | STDF 파싱 Worker | — |
| db | PostgreSQL 16 | localhost:5432 |
| rabbitmq | 메시지 큐 | http://localhost:15672 (ctdp / devpassword) |
| redis | 캐시 + Pub/Sub | localhost:6379 |
| frontend | React UI | http://localhost |

## 데모 시나리오

### 시나리오 1 — STDF 업로드 & 실시간 알림

1. `http://localhost` 에서 로그인
2. **Upload** 메뉴 → `.stdf` 파일 드래그 앤 드롭 → 업로드
3. Worker가 파일을 파싱하는 동안 UI에서 상태(대기→파싱→완료) 실시간 갱신 확인

### 시나리오 2 — Lot 분석

1. **Dashboard** 메뉴 → Lot 목록, FAIL률 확인
2. Lot 행 클릭 → Explorer 페이지에서 Wafer별 수율 확인
3. Part ID 입력 → 측정값(테스트명·결과·PASS/FAIL·알람) 테이블 조회

### 시나리오 3 — REST API (Swagger)

```bash
# 1. 로그인 → JWT 획득
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@example.com","password":"password123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Lot 목록 조회
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/lots | python3 -m json.tool

# 3. SSE 실시간 이벤트 수신
curl -N -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/events
```

## 프로젝트 구조

```
chip-test-data-platform/
├── backend/
│   ├── app/
│   │   ├── core/          # 설정, JWT/bcrypt, 의존성
│   │   ├── db/            # AsyncSession
│   │   ├── models/        # SQLAlchemy 모델 (13개 테이블)
│   │   ├── schemas/       # Pydantic 스키마
│   │   ├── routers/       # FastAPI 라우터
│   │   ├── services/      # 비즈니스 로직 (STDF 파서, 이벤트)
│   │   └── storage/       # 파일 스토리지 추상화 (로컬 ↔ S3)
│   ├── alembic/           # DB 마이그레이션
│   ├── docs/adr/          # 기술 의사결정 기록 (ADR 001~007)
│   └── tests/             # pytest (10개 테스트)
├── frontend/              # Vite + React + TypeScript
├── nginx/                 # 리버스 프록시 설정
└── docker-compose.yml
```

## 시스템 아키텍처

```
[Browser]──────────────────────────────────────────────────▶[Nginx :80]
                                                                 │
                              ┌──────────────────────────────────┤
                              │                                  │
                         /api/ ▼                            / ▼
                        [FastAPI]                       [Frontend]
                             │                         React + TS
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         [PostgreSQL]   [RabbitMQ]       [Redis]
          13 tables      stdf.parse    Cache-Aside
                              │         Pub/Sub
                              ▼              │
                          [Worker]      [SSE /events]
                        pystdf 파싱          │
                              │         [Browser]
                              └──────────────┘
                           publish → subscribe
```

## API 엔드포인트

전체 명세: **http://localhost/api/docs** (Swagger UI)

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
| `GET  /api/v1/users/me` | 내 프로필 조회 |

## 핵심 설계 결정

설계 근거: [`backend/docs/adr/`](backend/docs/adr/)

- **ADR-001 RabbitMQ 비동기 처리** — STDF 수신·파싱 분리, 202 즉시 응답, Worker 독립 확장
- **ADR-002 PostgreSQL + 완전 정규화** — measurements 수억 행, 복합 인덱스 + partial index
- **ADR-003 단일 코드베이스 / 별도 프로세스** — api·worker 공통 이미지, command로 역할 분리
- **ADR-004 파일 스토리지 추상화** — `StorageInterface` 1줄 교체로 로컬 → S3 전환
- **ADR-007 Redis Pub/Sub** — Worker publish → SSE bridge → 브라우저 실시간 이벤트

## 데이터 모델

13개 테이블 — 권한(roles, permissions, users), 도메인(osats, lots, wafers, parts, tests, measurements, stdf_files, file_processing_jobs), 감사(audit_logs).

```
lots (1) ──< wafers (N) ──< parts (N) ──< measurements (N)
                                              └── tests (FK)
```

## 개발 환경 (로컬)

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## 향후 계획

- [ ] S3 스토리지 백엔드 (`backend/app/storage/s3.py`)
- [ ] measurements 월별 Range 파티셔닝 (1억 행 도달 시)
- [ ] Prometheus + Grafana 모니터링
- [ ] CI/CD (GitHub Actions)
