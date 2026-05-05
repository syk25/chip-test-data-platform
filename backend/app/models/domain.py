from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import CIDR, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Osat(Base):
    __tablename__ = "osats"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    allowed_ip_cidrs: Mapped[list | None] = mapped_column(sa.ARRAY(CIDR))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    lots: Mapped[list["Lot"]] = relationship(back_populates="osat")
    stdf_files: Mapped[list["StdfFile"]] = relationship(back_populates="osat")


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    osat_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("osats.id", ondelete="RESTRICT"), nullable=False, index=True)
    lot_code: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    product_type: Mapped[str | None] = mapped_column(sa.String(100))
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    raw_mir: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    osat: Mapped["Osat"] = relationship(back_populates="lots")
    wafers: Mapped[list["Wafer"]] = relationship(back_populates="lot")
    stdf_files: Mapped[list["StdfFile"]] = relationship(back_populates="lot")


class StdfFile(Base):
    __tablename__ = "stdf_files"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    osat_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("osats.id", ondelete="RESTRICT"), nullable=False, index=True)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, sa.ForeignKey("lots.id", ondelete="RESTRICT"), index=True)
    filename: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(sa.String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    osat: Mapped["Osat"] = relationship(back_populates="stdf_files")
    lot: Mapped["Lot | None"] = relationship(back_populates="stdf_files")
    jobs: Mapped[list["FileProcessingJob"]] = relationship(back_populates="stdf_file", cascade="all, delete-orphan")


class FileProcessingJob(Base):
    __tablename__ = "file_processing_jobs"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    stdf_file_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("stdf_files.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, server_default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(sa.String(100))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    __table_args__ = (
        sa.CheckConstraint("status IN ('pending','processing','success','failure')", name="ck_job_status"),
    )

    stdf_file: Mapped["StdfFile"] = relationship(back_populates="jobs")


class Wafer(Base):
    __tablename__ = "wafers"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True)
    wafer_code: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("lot_id", "wafer_code", name="uq_wafers_lot_wafer_code"),
    )

    lot: Mapped["Lot"] = relationship(back_populates="wafers")
    parts: Mapped[list["Part"]] = relationship(back_populates="wafer")


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    wafer_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("wafers.id", ondelete="RESTRICT"), nullable=False, index=True)
    part_code: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    hard_bin: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    soft_bin: Mapped[int | None] = mapped_column(sa.SmallInteger)
    # is_pass: Generated Column (hard_bin = 1) — DB에서 자동 계산, Alembic DDL에서 정의
    is_pass: Mapped[bool] = mapped_column(sa.Computed("hard_bin = 1", persisted=True))
    x_coord: Mapped[int | None] = mapped_column(sa.SmallInteger)
    y_coord: Mapped[int | None] = mapped_column(sa.SmallInteger)
    head_num: Mapped[int | None] = mapped_column(sa.SmallInteger)
    site_num: Mapped[int | None] = mapped_column(sa.SmallInteger)
    is_retest: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.false())
    is_abnormal_end: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("wafer_id", "part_code", name="uq_parts_wafer_part_code"),
        sa.Index("ix_parts_wafer_pass", "wafer_id", "is_pass"),
        sa.Index("ix_parts_wafer_site", "wafer_id", "site_num"),
        sa.Index("ix_parts_retest", "is_retest"),
    )

    wafer: Mapped["Wafer"] = relationship(back_populates="parts")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="part")


class Test(Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    test_num: Mapped[int] = mapped_column(sa.Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    unit: Mapped[str | None] = mapped_column(sa.String(50))
    lo_limit: Mapped[float | None] = mapped_column(sa.Double)
    hi_limit: Mapped[float | None] = mapped_column(sa.Double)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    measurements: Mapped[list["Measurement"]] = relationship(back_populates="test")


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    test_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("tests.id", ondelete="RESTRICT"), nullable=False)
    result: Mapped[float | None] = mapped_column(sa.Double)
    is_pass: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    is_alarm: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    __table_args__ = (
        sa.Index("ix_measurements_part_test", "part_id", "test_id"),
        sa.Index("ix_measurements_part_pass", "part_id", "is_pass"),
        sa.Index("ix_measurements_test_time", "test_id", "created_at"),
        sa.Index("ix_measurements_alarm", "is_alarm", postgresql_where=sa.text("is_alarm = TRUE")),
    )

    part: Mapped["Part"] = relationship(back_populates="measurements")
    test: Mapped["Test"] = relationship(back_populates="measurements")
