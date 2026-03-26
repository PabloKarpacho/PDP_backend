import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import CONFIG
from src.models import Base


def _build_async_dsn(sync_dsn: str) -> str:
    if sync_dsn.startswith("postgresql+asyncpg://"):
        return sync_dsn
    if sync_dsn.startswith("postgresql+psycopg2://"):
        return sync_dsn.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if sync_dsn.startswith("postgresql://"):
        return sync_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return sync_dsn


db_semaphore = asyncio.Semaphore(150)

async_engine = create_async_engine(
    _build_async_dsn(CONFIG.POSTGRESQL_DSN),
    pool_size=50,
    max_overflow=100,
    pool_timeout=120,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_use_lifo=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with db_semaphore:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db():
        yield session


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return AsyncSessionLocal


async def init_models() -> None:
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
