import os
import uuid
from collections.abc import AsyncGenerator

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from appsec.api.deps import get_redis_client
from appsec.infrastructure.db.base import Base
from appsec.infrastructure.db.models import *  # noqa: F401,F403
from appsec.infrastructure.db.session import get_session
from appsec.main import create_app


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    async def ping(self) -> bool:
        return True


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session

    fake_redis = _FakeRedis()

    async def _override_get_redis() -> AsyncGenerator[_FakeRedis, None]:
        yield fake_redis

    app.dependency_overrides[get_redis_client] = _override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def random_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"
