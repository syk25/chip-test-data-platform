"""POST /api/v1/stdf-files — STDF 파일 업로드 (시나리오 1)."""
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connections import get_channel
from app.core.deps import get_client_ip, get_current_osat, get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.models.domain import FileProcessingJob, Osat
from app.schemas.stdf import JobStatusResponse, StdfUploadResponse
from app.services import audit
from app.services.stdf_upload import receive_stdf_file

router = APIRouter(prefix="/stdf-files", tags=["stdf"])
logger = structlog.get_logger()


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StdfUploadResponse,
    summary="STDF 파일 업로드 (비동기 처리)",
    description="OSAT: X-API-Key 헤더 | 내부 사용자: Bearer JWT. 202 즉시 반환.",
)
async def upload_stdf(
    request: Request,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    # 이중 인증: OSAT API 키 OR 내부 사용자 JWT (둘 중 하나)
    osat: Osat | None = Depends(lambda: None),  # 아래에서 수동 처리
) -> StdfUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".stdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="STDF 파일(.stdf)만 업로드 가능합니다.",
        )

    # 인증: X-API-Key (OSAT) 우선, 없으면 JWT (내부 사용자)
    api_key = request.headers.get("X-API-Key")
    osat_id: int
    uploaded_by: int | None = None

    if api_key:
        authenticated_osat = await get_current_osat(api_key=api_key, db=db)
        osat_id = authenticated_osat.id
        await audit.log(db, "stdf.upload.start", osat_id=osat_id,
                        resource_name=file.filename, ip_address=get_client_ip(request))
    else:
        from fastapi.security import HTTPBearer
        from app.core.deps import bearer_scheme, get_current_user
        from fastapi import Request as FR
        # JWT 검증
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="X-API-Key 또는 Bearer 토큰이 필요합니다.")
        from app.core.security import decode_access_token
        try:
            payload = decode_access_token(auth_header[7:])
            uploaded_by = int(payload["sub"])
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다.")
        osat_id = 1  # 내부 사용자는 기본 OSAT 사용
        await audit.log(db, "stdf.upload.start", user_id=uploaded_by,
                        resource_name=file.filename, ip_address=get_client_ip(request))

    channel = get_channel()
    result = await receive_stdf_file(
        file=file, osat_id=osat_id, uploaded_by=uploaded_by, db=db, channel=channel,
    )

    await audit.log(db, "stdf.upload.accepted", user_id=uploaded_by, osat_id=osat_id if api_key else None,
                    resource_type="stdf_file", resource_id=result.file_id, resource_name=result.filename)
    await db.commit()
    return result


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
