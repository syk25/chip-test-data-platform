import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = structlog.get_logger()

app = FastAPI(
    title="Chip Test Data Platform",
    description="STDF 파일 수집·파싱·저장·조회 백엔드 플랫폼",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    logger.info("api.started", environment=settings.ENVIRONMENT)


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("api.stopped")


@app.get("/api/v1/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


from app.routers import auth as auth_router

app.include_router(auth_router.router, prefix="/api/v1")
