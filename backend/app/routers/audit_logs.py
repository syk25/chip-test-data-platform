"""GET /api/v1/audit-logs — 감사 로그 조회 (Admin 전용, READ-ONLY)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.auth import User
from pydantic import BaseModel

router = APIRouter(prefix="/audit-logs", tags=["audit"])

admin_only = require_role("admin")


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    osat_id: int | None
    action: str
    resource_type: str | None
    resource_id: int | None
    resource_name: str | None
    status: str
    error_message: str | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get(
    "",
    response_model=list[AuditLogResponse],
    summary="감사 로그 조회 (Admin 전용)",
    description="INSERT-ONLY 테이블. 읽기만 가능. 기본 최근 30일.",
)
async def list_audit_logs(
    user_id: int | None = Query(None),
    osat_id: int | None = Query(None),
    action: str | None = Query(None),
    status: str | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
) -> list[AuditLogResponse]:
    # 기본 30일
    if not from_dt:
        from_dt = datetime.now(timezone.utc) - timedelta(days=30)
    if not to_dt:
        to_dt = datetime.now(timezone.utc)

    stmt = select(AuditLog).where(
        AuditLog.created_at >= from_dt,
        AuditLog.created_at <= to_dt,
    )
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if osat_id:
        stmt = stmt.where(AuditLog.osat_id == osat_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if status:
        stmt = stmt.where(AuditLog.status == status)

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    return [AuditLogResponse.model_validate(r) for r in result.scalars().all()]
