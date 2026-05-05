"""GET /api/v1/lots — Lot 조회 + 수율 통계 (시나리오 3)."""
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connections import get_redis
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.models.domain import Lot, Part, Wafer
from app.schemas.lots import LotDetail, LotSummary, WaferSummary

router = APIRouter(prefix="/lots", tags=["lots"])
logger = structlog.get_logger()

_CACHE_TTL = 300  # 5분 (ADR-002 Cache-Aside)


async def _lot_stats(lot_id: int, db: AsyncSession) -> dict:
    """Lot의 wafer/part 집계 — Cache-Aside (Redis TTL 5분)."""
    cache_key = f"cache:lot:{lot_id}:summary"
    redis = get_redis()

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # wafer 목록 + 각 wafer의 part 집계
    wafers_result = await db.execute(
        select(Wafer).where(Wafer.lot_id == lot_id).order_by(Wafer.id)
    )
    wafers = wafers_result.scalars().all()

    wafer_summaries = []
    total_parts = 0
    pass_parts = 0

    for w in wafers:
        count_result = await db.execute(
            select(func.count(Part.id), func.sum(func.cast(Part.is_pass, Integer)))
            .where(Part.wafer_id == w.id)
        )
        row = count_result.one()
        total = row[0] or 0
        passed = int(row[1] or 0)
        total_parts += total
        pass_parts += passed
        wafer_summaries.append({
            "id": w.id,
            "wafer_code": w.wafer_code,
            "started_at": w.started_at.isoformat() if w.started_at else None,
            "finished_at": w.finished_at.isoformat() if w.finished_at else None,
            "total_parts": total,
            "pass_parts": passed,
        })

    stats = {
        "wafer_count": len(wafers),
        "total_parts": total_parts,
        "pass_parts": pass_parts,
        "wafers": wafer_summaries,
    }
    await redis.set(cache_key, json.dumps(stats), ex=_CACHE_TTL)
    return stats


@router.get("", response_model=list[LotSummary], summary="Lot 목록 조회")
async def list_lots(
    osat_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[LotSummary]:
    stmt = select(Lot).order_by(Lot.created_at.desc()).offset((page - 1) * size).limit(size)
    if osat_id:
        stmt = stmt.where(Lot.osat_id == osat_id)

    result = await db.execute(stmt)
    lots = result.scalars().all()

    summaries = []
    for lot in lots:
        stats = await _lot_stats(lot.id, db)
        summaries.append(LotSummary(
            id=lot.id,
            lot_code=lot.lot_code,
            product_type=lot.product_type,
            started_at=lot.started_at,
            finished_at=lot.finished_at,
            created_at=lot.created_at,
            wafer_count=stats["wafer_count"],
            total_parts=stats["total_parts"],
            pass_parts=stats["pass_parts"],
        ))
    return summaries


@router.get("/{lot_id}", response_model=LotDetail, summary="Lot 상세 + 수율 통계")
async def get_lot(
    lot_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> LotDetail:
    lot = await db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot을 찾을 수 없습니다.")

    stats = await _lot_stats(lot_id, db)
    wafers = [WaferSummary(**w) for w in stats["wafers"]]

    return LotDetail(
        id=lot.id,
        lot_code=lot.lot_code,
        product_type=lot.product_type,
        started_at=lot.started_at,
        finished_at=lot.finished_at,
        created_at=lot.created_at,
        wafer_count=stats["wafer_count"],
        total_parts=stats["total_parts"],
        pass_parts=stats["pass_parts"],
        wafers=wafers,
    )
