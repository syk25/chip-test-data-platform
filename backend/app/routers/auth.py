from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_client_ip
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserRegister, UserResponse
from app.services import audit
from app.services.auth import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await register_user(data, db)
    await audit.log(db, "user.create", user_id=user.id, resource_type="user",
                    resource_id=user.id, resource_name=user.email, ip_address=get_client_ip(request))
    await db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        token = await login_user(data, db)
        # 로그인 성공 로그 (user_id 조회)
        from sqlalchemy import select
        from app.models.auth import User
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if user:
            await audit.log(db, "auth.login.success", user_id=user.id,
                            ip_address=get_client_ip(request),
                            user_agent=request.headers.get("User-Agent"))
            await db.commit()
        return token
    except Exception:
        await audit.log(db, "auth.login.failure", resource_name=data.email,
                        status="failure", ip_address=get_client_ip(request))
        await db.commit()
        raise
