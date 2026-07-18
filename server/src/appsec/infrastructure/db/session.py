from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from appsec.config import get_settings

settings = get_settings()

# statement_cache_size=0 is required when connecting through Supabase's
# transaction-mode pooler (port 6543): it multiplexes connections and does not
# support the prepared statements asyncpg caches by default. Harmless on a
# direct (5432) connection, so it's set unconditionally.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
