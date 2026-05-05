from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.connections import close_connections, init_connections

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_connections()
    logger.info("api.started", environment=settings.ENVIRONMENT)
    yield
    await close_connections()
    logger.info("api.stopped")


app = FastAPI(
    title="Chip Test Data Platform",
    description="STDF 파일 수집·파싱·저장·조회 백엔드 플랫폼",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# ── 라우터 등록 ──────────────────────────────────────────
from app.routers import audit_logs as audit_router  # Day 4
from app.routers import auth as auth_router          # Day 1
from app.routers import events as events_router      # Day 3
from app.routers import stdf as stdf_router          # Day 3
from app.routers import users as users_router        # Day 4

app.include_router(auth_router.router,   prefix="/api/v1")
app.include_router(stdf_router.router,   prefix="/api/v1")
app.include_router(events_router.router, prefix="/api/v1")
app.include_router(users_router.router,  prefix="/api/v1")
app.include_router(audit_router.router,  prefix="/api/v1")
# Day 5: lots, measurements 라우터 추가 예정
