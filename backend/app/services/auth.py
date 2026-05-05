from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.auth import Role, User
from app.schemas.auth import LoginRequest, TokenResponse, UserRegister, UserResponse


async def register_user(data: UserRegister, db: AsyncSession) -> UserResponse:
    # 이메일 중복 확인
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")

    # role_id 유효성 확인
    role = await db.get(Role, data.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="존재하지 않는 역할입니다.")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role_id=data.role_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def login_user(data: LoginRequest, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다.")

    # role 이름 조회 (JWT payload에 포함)
    role = await db.get(Role, user.role_id)
    token = create_access_token(subject=str(user.id), role=role.name if role else "engineer")
    return TokenResponse(access_token=token)
