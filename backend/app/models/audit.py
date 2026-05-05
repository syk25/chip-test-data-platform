from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    osat_id: Mapped[int | None] = mapped_column(sa.BigInteger, sa.ForeignKey("osats.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(sa.String(100))
    resource_id: Mapped[int | None] = mapped_column(sa.BigInteger)
    resource_name: Mapped[str | None] = mapped_column(sa.String(500))
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, server_default="success")
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    changes: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), index=True)

    __table_args__ = (
        # 행위자: user 또는 osat, 익명(둘 다 NULL) 허용
        sa.CheckConstraint(
            "NOT (user_id IS NOT NULL AND osat_id IS NOT NULL)",
            name="ck_audit_actor_exclusive",
        ),
        sa.CheckConstraint("status IN ('success','failure')", name="ck_audit_status"),
        # 정규식 패턴: <resource>.<verb>[.<modifier>]
        sa.CheckConstraint(
            r"action ~ '^[a-z_]+\.[a-z_]+(\.[a-z_]+)?$'",
            name="ck_audit_action_format",
        ),
        sa.Index("ix_audit_user_time", "user_id", "created_at"),
        sa.Index("ix_audit_osat_time", "osat_id", "created_at"),
        sa.Index("ix_audit_resource", "resource_type", "resource_id", "created_at"),
        sa.Index("ix_audit_action_time", "action", "created_at"),
        sa.Index("ix_audit_ip_time", "ip_address", "created_at"),
        sa.Index("ix_audit_failure", "status", postgresql_where=sa.text("status = 'failure'")),
    )
