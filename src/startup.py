from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import CONFIG
from src.database_control.s3 import ensure_bucket_exists
from src.logger import logger


StartupRunner = Callable[[], Awaitable[None]]
BucketInitializer = Callable[[str], Awaitable[None]]


async def ensure_minio_bucket_ready(
    bucket_name: str,
    *,
    bucket_initializer: BucketInitializer = ensure_bucket_exists,
    endpoint_url: str = CONFIG.MINIO_ENDPOINT,
) -> None:
    extra = {
        "bucket_name": bucket_name,
        "endpoint_url": endpoint_url,
    }
    logger.info("Ensuring MinIO bucket exists.", extra=extra)
    try:
        await bucket_initializer(bucket_name)
    except Exception as exc:
        logger.error("MinIO bucket initialization failed.", extra=extra)
        logger.dump()
        raise RuntimeError(
            f"MinIO bucket initialization failed for '{bucket_name}' at '{endpoint_url}'."
        ) from exc

    logger.info("MinIO bucket is ready.", extra=extra)
    logger.dump()


async def run_startup_tasks() -> None:
    await ensure_minio_bucket_ready(CONFIG.MINIO_FILES_BUCKET_NAME)


def create_lifespan(startup_runner: StartupRunner = run_startup_tasks):
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await startup_runner()
        yield

    return lifespan
