"""API 기본 테스트 — 핵심 엔드포인트 동작 확인."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Role


# ── 헬퍼 ─────────────────────────────────────────────────

async def _seed_role(db: AsyncSession) -> None:
    """테스트 DB에 기본 역할 시드."""
    from sqlalchemy import select
    result = await db.execute(select(Role).where(Role.name == "engineer"))
    if not result.scalar_one_or_none():
        db.add(Role(id=3, name="engineer", description="테스트용"))
        await db.commit()


async def _register_and_login(client: AsyncClient, db: AsyncSession) -> str:
    await _seed_role(db)
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "TestPass123!",
        "name": "테스트유저",
        "role_id": 3,
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123!",
    })
    return resp.json()["access_token"]


# ── 테스트 ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """GET /api/v1/health → 200 ok."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db: AsyncSession) -> None:
    """POST /auth/register → 201, 이메일·이름 반환."""
    await _seed_role(db)
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "Pass1234!",
        "name": "신규유저",
        "role_id": 3,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db: AsyncSession) -> None:
    """중복 이메일 → 409 Conflict."""
    await _seed_role(db)
    payload = {"email": "dup@example.com", "password": "P@ss1234", "name": "A", "role_id": 3}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db: AsyncSession) -> None:
    """로그인 → access_token 반환."""
    token = await _register_and_login(client, db)
    assert isinstance(token, str) and len(token) > 10


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db: AsyncSession) -> None:
    """잘못된 비밀번호 → 401."""
    await _seed_role(db)
    await client.post("/api/v1/auth/register", json={
        "email": "wp@example.com", "password": "Correct1!", "name": "X", "role_id": 3,
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wp@example.com", "password": "Wrong!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_lots_requires_auth(client: AsyncClient) -> None:
    """인증 없이 /lots → 401."""
    resp = await client.get("/api/v1/lots")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_lots_empty_with_auth(client: AsyncClient, db: AsyncSession) -> None:
    """인증 후 /lots → 200, 빈 배열."""
    token = await _register_and_login(client, db)
    resp = await client.get("/api/v1/lots", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_measurements_requires_part_id(client: AsyncClient, db: AsyncSession) -> None:
    """part_id 없이 /measurements → 422 (필수 파라미터 누락)."""
    token = await _register_and_login(client, db)
    resp = await client.get("/api/v1/measurements", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_measurements_invalid_part_id(client: AsyncClient, db: AsyncSession) -> None:
    """존재하지 않는 part_id → 400."""
    token = await _register_and_login(client, db)
    resp = await client.get(
        "/api/v1/measurements?part_id=99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_users_me(client: AsyncClient, db: AsyncSession) -> None:
    """GET /users/me → 내 정보 반환."""
    token = await _register_and_login(client, db)
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"
