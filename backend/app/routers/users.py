"""GET /api/v1/users — 사용자 관리 (Admin 전용)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.auth import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])

admin_only = require_role("admin")


@router.get("", response_model=list[UserResponse], summary="전체 사용자 목록 (Admin)")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
) -> list[UserResponse]:
    result = await db.execute(select(User).order_by(User.id))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.get("/me", response_model=UserResponse, summary="내 정보 조회")
async def get_me(
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    from app.core.deps import get_current_user
    from fastapi import Request
    # 간단하게 구현 — auth 라우터의 get_current_user Depends 재사용
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="구현 예정")


@router.patch("/{user_id}/deactivate", response_model=UserResponse, summary="사용자 비활성화 (Admin)")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
) -> UserResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
