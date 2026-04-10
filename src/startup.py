from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import asynccontextmanager

import aioboto3
from botocore.exceptions import NoCredentialsError
from fastapi import FastAPI

from src.config import CONFIG
from src.database_control.s3 import ensure_bucket_exists
from src.logger import logger


StartupRunner = Callable[[], Awaitable[None]]
BucketInitializer = Callable[[str], Awaitable[None]]


AWS_CREDENTIALS_ERROR_MESSAGE = (
    "AWS credentials are not available. If the backend runs inside Docker on EC2, "
    "attach an IAM role to the instance and ensure EC2 Instance Metadata is enabled "
    "with IMDS access available to containers. For IMDSv2 on Docker, set "
    "HttpPutResponseHopLimit to at least 2."
)


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


async def ensure_aws_credentials_ready() -> None:
    extra = {
        "storage_backend": CONFIG.STORAGE_BACKEND,
        "storage_region": CONFIG.STORAGE_REGION,
    }
    logger.info("Validating AWS credentials for storage backend.", extra=extra)
    try:
        session = aioboto3.Session(region_name=CONFIG.STORAGE_REGION)
        async with session.client("sts") as sts:
            await sts.get_caller_identity()
    except NoCredentialsError as exc:
        logger.error(AWS_CREDENTIALS_ERROR_MESSAGE, extra=extra)
        logger.dump()
        raise RuntimeError(AWS_CREDENTIALS_ERROR_MESSAGE) from exc
    except Exception as exc:
        logger.error("AWS credential validation failed.", extra=extra)
        logger.dump()
        raise RuntimeError(
            "AWS credential validation failed. Check IAM role attachment, "
            "instance metadata access, and network reachability to AWS STS."
        ) from exc

    logger.info("AWS credentials are ready for storage backend.", extra=extra)
    logger.dump()


async def run_startup_tasks() -> None:
    if CONFIG.STORAGE_BACKEND == "aws":
        # await ensure_aws_credentials_ready()
        return

    await ensure_minio_bucket_ready(CONFIG.FILES_BUCKET_NAME)


def create_lifespan(startup_runner: StartupRunner = run_startup_tasks):
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("Application startup started.")
        try:
            await startup_runner()
        except Exception as error:
            logger.error(
                "Application startup failed.",
                extra={"error_type": type(error).__name__},
            )
            logger.dump()
            raise

        logger.info("Application startup completed.")
        logger.dump()

        try:
            yield
        finally:
            logger.info("Application shutdown completed.")
            logger.dump()

    return lifespan
