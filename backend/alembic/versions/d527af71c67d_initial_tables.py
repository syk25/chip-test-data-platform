"""initial tables — 13개 테이블 생성 + 기본 역할 시드

Revision ID: d527af71c67d
Revises:
Create Date: 2026-05-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import CIDR, INET, JSONB

revision: str = "d527af71c67d"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 권한 관리 ──────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role_id", "users", ["role_id"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.BigInteger(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── 도메인 ────────────────────────────────────────────────
    op.create_table(
        "osats",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("api_key_hash", sa.String(255), nullable=False),
        sa.Column("allowed_ip_cidrs", sa.ARRAY(CIDR()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "lots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("osat_id", sa.BigInteger(), sa.ForeignKey("osats.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lot_code", sa.String(100), nullable=False, unique=True),
        sa.Column("product_type", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_mir", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lots_osat_id", "lots", ["osat_id"])

    op.create_table(
        "stdf_files",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("osat_id", sa.BigInteger(), sa.ForeignKey("osats.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lot_id", sa.BigInteger(), sa.ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stdf_files_osat_id", "stdf_files", ["osat_id"])
    op.create_index("ix_stdf_files_lot_id", "stdf_files", ["lot_id"])

    op.create_table(
        "file_processing_jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stdf_file_id", sa.BigInteger(), sa.ForeignKey("stdf_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending','processing','success','failure')", name="ck_job_status"),
    )
    op.create_index("ix_file_processing_jobs_stdf_file_id", "file_processing_jobs", ["stdf_file_id"])
    op.create_index("ix_file_processing_jobs_status", "file_processing_jobs", ["status"])

    op.create_table(
        "wafers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("lot_id", sa.BigInteger(), sa.ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("wafer_code", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("lot_id", "wafer_code", name="uq_wafers_lot_wafer_code"),
    )
    op.create_index("ix_wafers_lot_id", "wafers", ["lot_id"])

    op.create_table(
        "tests",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("test_num", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("lo_limit", sa.Double(), nullable=True),
        sa.Column("hi_limit", sa.Double(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "parts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("wafer_id", sa.BigInteger(), sa.ForeignKey("wafers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("part_code", sa.String(100), nullable=False),
        sa.Column("hard_bin", sa.SmallInteger(), nullable=False),
        sa.Column("soft_bin", sa.SmallInteger(), nullable=True),
        sa.Column("is_pass", sa.Boolean(), sa.Computed("hard_bin = 1", persisted=True)),
        sa.Column("x_coord", sa.SmallInteger(), nullable=True),
        sa.Column("y_coord", sa.SmallInteger(), nullable=True),
        sa.Column("head_num", sa.SmallInteger(), nullable=True),
        sa.Column("site_num", sa.SmallInteger(), nullable=True),
        sa.Column("is_retest", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_abnormal_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("wafer_id", "part_code", name="uq_parts_wafer_part_code"),
    )
    op.create_index("ix_parts_wafer_id", "parts", ["wafer_id"])
    op.create_index("ix_parts_wafer_pass", "parts", ["wafer_id", "is_pass"])
    op.create_index("ix_parts_wafer_site", "parts", ["wafer_id", "site_num"])
    op.create_index("ix_parts_retest", "parts", ["is_retest"])

    op.create_table(
        "measurements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("part_id", sa.BigInteger(), sa.ForeignKey("parts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_id", sa.BigInteger(), sa.ForeignKey("tests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("result", sa.Double(), nullable=True),
        sa.Column("is_pass", sa.Boolean(), nullable=False),
        sa.Column("is_alarm", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_measurements_part_test", "measurements", ["part_id", "test_id"])
    op.create_index("ix_measurements_part_pass", "measurements", ["part_id", "is_pass"])
    op.create_index("ix_measurements_test_time", "measurements", ["test_id", "created_at"])
    op.create_index(
        "ix_measurements_alarm", "measurements", ["is_alarm"],
        postgresql_where=sa.text("is_alarm = TRUE"),
    )

    # ── 감사 로그 ─────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("osat_id", sa.BigInteger(), sa.ForeignKey("osats.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.BigInteger(), nullable=True),
        sa.Column("resource_name", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("changes", JSONB(), nullable=True),
        sa.Column("ip_address", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "NOT (user_id IS NOT NULL AND osat_id IS NOT NULL)",
            name="ck_audit_actor_exclusive",
        ),
        sa.CheckConstraint("status IN ('success','failure')", name="ck_audit_status"),
        sa.CheckConstraint(
            r"action ~ '^[a-z_]+\.[a-z_]+(\.[a-z_]+)?$'",
            name="ck_audit_action_format",
        ),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_user_time", "audit_logs", ["user_id", "created_at"])
    op.create_index("ix_audit_logs_osat_time", "audit_logs", ["osat_id", "created_at"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id", "created_at"])
    op.create_index("ix_audit_logs_action_time", "audit_logs", ["action", "created_at"])
    op.create_index("ix_audit_logs_ip_time", "audit_logs", ["ip_address", "created_at"])
    op.create_index(
        "ix_audit_logs_failure", "audit_logs", ["status"],
        postgresql_where=sa.text("status = 'failure'"),
    )

    # ── 시드: 기본 역할 3개 ────────────────────────────────────
    op.execute("""
        INSERT INTO roles (name, description) VALUES
        ('admin',    '시스템 관리자 — 사용자 계정 관리 및 시스템 설정'),
        ('lead',     '팀 리더 — 전체 데이터 열람 및 삭제'),
        ('engineer', '검증 엔지니어 — STDF 업로드 및 데이터 조회')
    """)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("measurements")
    op.drop_table("parts")
    op.drop_table("tests")
    op.drop_table("wafers")
    op.drop_table("file_processing_jobs")
    op.drop_table("stdf_files")
    op.drop_table("lots")
    op.drop_table("osats")
    op.drop_table("role_permissions")
    op.drop_table("users")
    op.drop_table("permissions")
    op.drop_table("roles")
