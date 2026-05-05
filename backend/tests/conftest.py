"""pytest 공유 픽스처 — 테스트당 독립 DB 세션."""
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DB_URL = "postgresql+asyncpg://ctdp:devpassword@localhost:5432/chip_test_db_test"


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """테스트마다 스키마를 초기화하고 세션을 제공."""
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db

    import app.core.connections as conn_module
    mock_ch = MagicMock()
    mock_ch.default_exchange.publish = AsyncMock()
    conn_module._rabbitmq_channel = mock_ch

    mock_r = AsyncMock()
    mock_r.get = AsyncMock(return_value=None)
    mock_r.set = AsyncMock()
    mock_r.publish = AsyncMock()
    conn_module._redis = mock_r

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
