"""FastAPI 공통 의존성 — JWT 인증, RBAC 권한 체크, OSAT API 키 인증."""
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.auth import User
from app.models.domain import Osat

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ── JWT 인증 ──────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Bearer 토큰을 검증하고 현재 사용자를 반환."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 토큰이 필요합니다.")

    try:
        import jwt
        payload = decode_access_token(credentials.credentials)
        user_id: int = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다.")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="비활성화된 계정입니다.")

    return user


def require_role(*roles: str):
    """특정 역할만 허용하는 의존성 팩토리."""
    async def _check(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
        from app.models.auth import Role
        role = await db.get(Role, user.role_id)
        if not role or role.name not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"이 작업은 {', '.join(roles)} 역할만 수행할 수 있습니다.",
            )
        return user
    return _check


# ── OSAT API 키 인증 ──────────────────────────────────────

async def get_current_osat(
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Osat:
    """X-API-Key 헤더로 OSAT를 식별하고 반환."""
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key 헤더가 필요합니다.")

    from app.core.security import verify_password
    result = await db.execute(select(Osat).where(Osat.is_active == True))  # noqa: E712
    osats = result.scalars().all()

    for osat in osats:
        if verify_password(api_key, osat.api_key_hash):
            return osat

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 API 키입니다.")


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None
