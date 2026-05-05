"""GET /api/v1/measurements — 측정값 조회 (시나리오 6, part_id 필수)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.models.domain import Measurement, Part, Test
from app.schemas.lots import MeasurementResponse

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.get(
    "",
    response_model=list[MeasurementResponse],
    summary="측정값 조회 (part_id 필수 — 30억 행 테이블 보호)",
)
async def list_measurements(
    part_id: int = Query(..., description="필수. 특정 Part의 측정값만 조회 가능."),
    is_pass: bool | None = Query(None),
    is_alarm: bool | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MeasurementResponse]:
    # part_id 유효성 확인 — 라우터 레벨에서 DB 도달 전 차단 (ADR-002)
    part = await db.get(Part, part_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="존재하지 않는 part_id입니다.",
        )

    stmt = (
        select(Measurement, Test.test_num, Test.name, Test.unit)
        .join(Test, Measurement.test_id == Test.id)
        .where(Measurement.part_id == part_id)
    )
    if is_pass is not None:
        stmt = stmt.where(Measurement.is_pass == is_pass)
    if is_alarm is not None:
        stmt = stmt.where(Measurement.is_alarm == is_alarm)

    stmt = stmt.order_by(Measurement.id).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)

    rows = result.all()
    return [
        MeasurementResponse(
            id=m.id,
            part_id=m.part_id,
            test_id=m.test_id,
            test_num=test_num,
            test_name=name,
            unit=unit,
            result=m.result,
            is_pass=m.is_pass,
            is_alarm=m.is_alarm,
            created_at=m.created_at,
        )
        for m, test_num, name, unit in rows
    ]
