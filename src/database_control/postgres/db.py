import asyncio
from collections.abc import AsyncIterator
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
import ssl

from alembic import command
from alembic.config import Config as AlembicConfig
import boto3
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import CONFIG


def _build_async_dsn(sync_dsn: str) -> str:
    if sync_dsn.startswith("postgresql+asyncpg://"):
        return sync_dsn
    if sync_dsn.startswith("postgresql+psycopg2://"):
        return sync_dsn.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if sync_dsn.startswith("postgresql://"):
        return sync_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return sync_dsn


def _build_sync_dsn(async_dsn: str) -> str:
    if async_dsn.startswith("postgresql+asyncpg://"):
        return async_dsn.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return async_dsn


@dataclass(frozen=True)
class DatabaseRuntimeConfig:
    async_dsn: str
    sync_dsn: str
    async_connect_args: dict[str, ssl.SSLContext | bool]


def _load_aws_database_secret(
    secret_arn: str, region_name: str
) -> dict[str, str | int | None]:
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_arn)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError("Secrets Manager response did not contain SecretString")

    secret_payload = json.loads(secret_string)
    if not isinstance(secret_payload, dict):
        raise ValueError("Secrets Manager secret payload must be a JSON object")

    return secret_payload


def _build_rds_ssl_context(ssl_root_cert: str) -> ssl.SSLContext:
    ssl_context = ssl.create_default_context(cafile=ssl_root_cert)
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    return ssl_context


def _build_asyncpg_ssl_config(
    aws_ssl_mode: str,
    aws_ssl_root_cert: str,
    ssl_context_builder: Callable[[str], ssl.SSLContext],
) -> dict[str, ssl.SSLContext | bool]:
    normalized_ssl_mode = aws_ssl_mode.strip().lower()
    if normalized_ssl_mode == "disable":
        return {"ssl": False}
    if normalized_ssl_mode in {"require", "allow", "prefer"}:
        return {"ssl": True}
    return {"ssl": ssl_context_builder(aws_ssl_root_cert)}


def _build_database_runtime_config(
    *,
    database_backend: str,
    local_dsn: str,
    aws_region: str,
    aws_secret_arn: str,
    aws_host: str,
    aws_port: int,
    aws_database: str,
    aws_user: str,
    aws_ssl_mode: str,
    aws_ssl_root_cert: str,
    secret_loader: Callable[
        [str, str], dict[str, str | int | None]
    ] = _load_aws_database_secret,
    ssl_context_builder: Callable[[str], ssl.SSLContext] = _build_rds_ssl_context,
) -> DatabaseRuntimeConfig:
    if database_backend != "aws":
        async_dsn = _build_async_dsn(local_dsn)
        return DatabaseRuntimeConfig(
            async_dsn=async_dsn,
            sync_dsn=_build_sync_dsn(async_dsn),
            async_connect_args={},
        )

    secret_payload = secret_loader(aws_secret_arn, aws_region)
    password = secret_payload.get("password")
    if not isinstance(password, str) or not password:
        raise ValueError(
            "Secrets Manager secret payload must contain a non-empty password"
        )

    async_url = URL.create(
        drivername="postgresql+asyncpg",
        username=aws_user,
        password=password,
        host=aws_host,
        port=aws_port,
        database=aws_database,
    )
    sync_url = URL.create(
        drivername="postgresql+psycopg2",
        username=aws_user,
        password=password,
        host=aws_host,
        port=aws_port,
        database=aws_database,
        query=(
            {
                "sslmode": aws_ssl_mode,
                "sslrootcert": aws_ssl_root_cert,
            }
            if aws_ssl_root_cert
            else {"sslmode": aws_ssl_mode}
        ),
    )
    return DatabaseRuntimeConfig(
        async_dsn=async_url.render_as_string(hide_password=False),
        sync_dsn=sync_url.render_as_string(hide_password=False),
        async_connect_args=_build_asyncpg_ssl_config(
            aws_ssl_mode,
            aws_ssl_root_cert,
            ssl_context_builder,
        ),
    )


@lru_cache(maxsize=1)
def get_database_runtime_config() -> DatabaseRuntimeConfig:
    return _build_database_runtime_config(
        database_backend=CONFIG.DATABASE_BACKEND,
        local_dsn=CONFIG.POSTGRESQL_DSN,
        aws_region=CONFIG.AWS_POSTGRES_REGION,
        aws_secret_arn=CONFIG.AWS_POSTGRES_SECRET_ARN,
        aws_host=CONFIG.AWS_POSTGRES_HOST,
        aws_port=CONFIG.AWS_POSTGRES_PORT,
        aws_database=CONFIG.AWS_POSTGRES_DB,
        aws_user=CONFIG.AWS_POSTGRES_USER,
        aws_ssl_mode=CONFIG.AWS_POSTGRES_SSL_MODE,
        aws_ssl_root_cert=CONFIG.AWS_POSTGRES_SSL_ROOT_CERT,
    )


db_semaphore = asyncio.Semaphore(150)
database_runtime_config = get_database_runtime_config()

async_engine = create_async_engine(
    database_runtime_config.async_dsn,
    pool_size=50,
    max_overflow=100,
    pool_timeout=120,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_use_lifo=True,
    connect_args=database_runtime_config.async_connect_args,
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


def build_alembic_config(database_dsn: str | None = None) -> AlembicConfig:
    project_root = Path(__file__).resolve().parents[3]
    alembic_config = AlembicConfig(str(project_root / "alembic.ini"))
    resolved_dsn = (
        _build_sync_dsn(database_dsn)
        if database_dsn is not None
        else get_database_runtime_config().sync_dsn
    )
    alembic_config.set_main_option(
        "sqlalchemy.url",
        resolved_dsn,
    )
    return alembic_config


def upgrade_database_head(database_dsn: str | None = None) -> None:
    alembic_config = build_alembic_config(database_dsn)
    command.upgrade(alembic_config, "head")


async def upgrade_database_head_async(database_dsn: str | None = None) -> None:
    await asyncio.to_thread(upgrade_database_head, database_dsn)
