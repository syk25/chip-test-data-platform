"""POST /api/v1/stdf-files — STDF 파일 업로드 (시나리오 1)."""
import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connections import get_channel
from app.db.session import get_db
from app.models.domain import FileProcessingJob
from app.schemas.stdf import JobStatusResponse, StdfUploadResponse
from app.services.stdf_upload import receive_stdf_file

router = APIRouter(prefix="/stdf-files", tags=["stdf"])
logger = structlog.get_logger()

# TODO Day 4: OSAT API 키 인증 미들웨어 추가
# 현재는 osat_id=1 하드코딩 (데모용), Day 4에서 X-API-Key 헤더로 OSAT 식별


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StdfUploadResponse,
    summary="STDF 파일 업로드 (비동기 처리)",
    description="파일을 접수하고 즉시 202 반환. 백그라운드에서 RabbitMQ → Worker가 파싱.",
)
async def upload_stdf(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> StdfUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".stdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="STDF 파일(.stdf)만 업로드 가능합니다.",
        )

    channel = get_channel()
    return await receive_stdf_file(
        file=file,
        osat_id=1,          # TODO Day 4: API 키로 osat_id 조회
        uploaded_by=None,   # TODO Day 4: JWT에서 user_id 추출
        db=db,
        channel=channel,
    )


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="처리 상태 조회 (polling)",
)
async def get_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    job = await db.get(FileProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job을 찾을 수 없습니다.")
    return JobStatusResponse.model_validate(job)
