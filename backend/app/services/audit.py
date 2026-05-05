"""Audit Log 자동 기록 서비스."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log(
    db: AsyncSession,
    action: str,
    *,
    user_id: int | None = None,
    osat_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    resource_name: str | None = None,
    status: str = "success",
    error_message: str | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """audit_logs 테이블에 행위 기록. INSERT-only, 절대 수정/삭제 안 함."""
    entry = AuditLog(
        user_id=user_id,
        osat_id=osat_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        status=status,
        error_message=error_message,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    # 호출자가 commit 책임 (트랜잭션 일관성 유지)
