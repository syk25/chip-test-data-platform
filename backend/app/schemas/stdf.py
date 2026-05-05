from datetime import datetime

from pydantic import BaseModel


class StdfUploadResponse(BaseModel):
    """202 Accepted 응답 — 파일 접수 확인 + job 추적용 ID 제공."""
    file_id: int
    job_id: int
    filename: str
    status: str = "pending"
    message: str = "파일이 접수됐습니다. job_id로 처리 상태를 확인하세요."


class JobStatusResponse(BaseModel):
    job_id: int
    file_id: int
    status: str          # pending | processing | success | failure
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
