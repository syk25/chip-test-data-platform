"""pystdf로 STDF 파일을 파싱해 PostgreSQL에 저장."""
import io
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Lot, Measurement, Part, StdfFile, Test, Wafer

logger = structlog.get_logger()


def _ts(stdf_epoch: int | None) -> datetime | None:
    """STDF 타임스탬프(UTC 초) → datetime."""
    if not stdf_epoch:
        return None
    return datetime.fromtimestamp(stdf_epoch, tz=timezone.utc)


def _getattr_safe(record: Any, *names: str, default: Any = None) -> Any:
    """레코드에서 필드 값을 안전하게 읽음 (None, 빈 문자열, 0xFFFFFFFF 제외)."""
    for name in names:
        val = getattr(record, name, None)
        if val is not None and val != "" and val != 4294967295:
            return val
    return default


def _parse_stdf(file_data: bytes) -> list[tuple[str, Any]]:
    """STDF 바이트 → (type_name, record) 리스트.

    pystdf의 싱크(sink) 기반 API를 사용해 레코드를 수집한 뒤,
    각 레코드를 SimpleNamespace로 변환해 속성 접근이 가능하도록 한다.
    """
    from pystdf.IO import Parser as StdfParser

    records: list[tuple[str, Any]] = []

    class _Sink:
        def before_send(self, source: Any, data: Any) -> None:  # noqa: ANN001
            rectype, fields = data
            rec = SimpleNamespace(**dict(zip(rectype.columnNames, fields)))
            records.append((type(rectype).__name__, rec))

    with io.BytesIO(file_data) as buf:
        parser = StdfParser(inp=buf)
        parser.addSink(_Sink())
        parser.parse()

    return records


async def _get_or_create_test(test_num: int, ptr: Any, db: AsyncSession) -> int:
    """tests 마스터 테이블에서 test_num으로 조회, 없으면 생성."""
    result = await db.execute(select(Test).where(Test.test_num == test_num))
    test = result.scalar_one_or_none()
    if test:
        return test.id

    test = Test(
        test_num=test_num,
        name=_getattr_safe(ptr, "TEST_TXT", default=f"Test {test_num}"),
        unit=_getattr_safe(ptr, "UNITS"),
        lo_limit=_getattr_safe(ptr, "LO_LIMIT"),
        hi_limit=_getattr_safe(ptr, "HI_LIMIT"),
    )
    db.add(test)
    await db.flush()
    return test.id


async def parse_and_save(
    file_data: bytes,
    stdf_file_id: int,
    osat_id: int,
    db: AsyncSession,
) -> int:
    """STDF 바이트 데이터를 파싱해 DB에 저장하고 lot_id를 반환."""
    lot: Lot | None = None
    current_wafer: Wafer | None = None
    pending_ptrs: list[tuple[int, Any]] = []  # (test_num, ptr_record)
    test_id_cache: dict[int, int] = {}

    for type_name, recdata in _parse_stdf(file_data):

        # ── MIR: Lot 생성 ──────────────────────────────────────────────────
        if type_name == "Mir":
            lot_code = _getattr_safe(recdata, "LOT_ID") or f"LOT_{stdf_file_id}"

            result = await db.execute(select(Lot).where(Lot.lot_code == lot_code))
            lot = result.scalar_one_or_none()

            if not lot:
                lot = Lot(
                    osat_id=osat_id,
                    lot_code=lot_code,
                    product_type=_getattr_safe(recdata, "PART_TYP"),
                    started_at=_ts(_getattr_safe(recdata, "START_T")),
                    raw_mir={k: str(v) for k, v in vars(recdata).items() if v is not None},
                )
                db.add(lot)
                await db.flush()

            stdf_rec = await db.get(StdfFile, stdf_file_id)
            if stdf_rec:
                stdf_rec.lot_id = lot.id
                await db.flush()

        # ── WIR: Wafer 시작 ────────────────────────────────────────────────
        elif type_name == "Wir" and lot:
            wafer_code = _getattr_safe(recdata, "WAFER_ID") or f"W{_getattr_safe(recdata, 'HEAD_NUM', default=0)}"
            current_wafer = Wafer(
                lot_id=lot.id,
                wafer_code=str(wafer_code),
                started_at=_ts(_getattr_safe(recdata, "START_T")),
            )
            db.add(current_wafer)
            await db.flush()
            pending_ptrs.clear()

        # ── PIR: Part 시작 ─────────────────────────────────────────────────
        elif type_name == "Pir":
            pending_ptrs.clear()

        # ── PTR: 측정값 누적 ───────────────────────────────────────────────
        elif type_name == "Ptr":
            test_num = _getattr_safe(recdata, "TEST_NUM")
            if test_num is not None:
                pending_ptrs.append((test_num, recdata))

        # ── PRR: Part + Measurements 저장 ─────────────────────────────────
        elif type_name == "Prr" and current_wafer:
            hard_bin = _getattr_safe(recdata, "HARD_BIN", default=0)
            part = Part(
                wafer_id=current_wafer.id,
                part_code=_getattr_safe(recdata, "PART_ID") or f"PART_{current_wafer.id}_{hard_bin}",
                hard_bin=hard_bin,
                soft_bin=_getattr_safe(recdata, "SOFT_BIN"),
                x_coord=_getattr_safe(recdata, "X_COORD"),
                y_coord=_getattr_safe(recdata, "Y_COORD"),
                head_num=_getattr_safe(recdata, "HEAD_NUM"),
                site_num=_getattr_safe(recdata, "SITE_NUM"),
            )
            db.add(part)
            await db.flush()

            for test_num, ptr in pending_ptrs:
                if test_num not in test_id_cache:
                    test_id_cache[test_num] = await _get_or_create_test(test_num, ptr, db)

                test_flag = _getattr_safe(ptr, "TEST_FLG", default=0)
                result_val = _getattr_safe(ptr, "RESULT")
                is_pass = not bool(test_flag & 0x80) if test_flag is not None else True

                measurement = Measurement(
                    part_id=part.id,
                    test_id=test_id_cache[test_num],
                    result=float(result_val) if result_val is not None else None,
                    is_pass=is_pass,
                    is_alarm=bool(test_flag & 0x01) if test_flag is not None else False,
                )
                db.add(measurement)

            pending_ptrs.clear()
            await db.flush()

        # ── WRR: Wafer 종료 ────────────────────────────────────────────────
        elif type_name == "Wrr" and current_wafer:
            current_wafer.finished_at = _ts(_getattr_safe(recdata, "FINISH_T"))
            await db.flush()

        # ── MRR: Lot 종료 ──────────────────────────────────────────────────
        elif type_name == "Mrr" and lot:
            lot.finished_at = _ts(_getattr_safe(recdata, "FINISH_T"))
            await db.flush()

    await db.commit()
    logger.info("stdf.parsed", lot_id=lot.id if lot else None, file_id=stdf_file_id)
    return lot.id if lot else 0
