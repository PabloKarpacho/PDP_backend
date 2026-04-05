from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from typing import BinaryIO
import re
import unicodedata
import uuid

import aioboto3
from loguru import logger

from src.config import CONFIG


_FILENAME_SAFE_CHARS_PATTERN = re.compile(r"[^a-z0-9]+")


class StorageError(Exception):
    """Raised when S3-compatible storage operations fail."""


@dataclass(frozen=True)
class StoredObject:
    bucket_name: str
    key: str
    content_type: str | None
    size: int
    metadata: dict[str, str] | None = None


def sanitize_storage_filename(filename: str | None) -> str:
    raw_filename = (filename or "").replace("\\", "/")
    basename = PurePath(raw_filename).name.strip()
    if not basename:
        return "file"

    ascii_filename = (
        unicodedata.normalize("NFKD", basename)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    ascii_filename = ascii_filename.strip().lower()

    stem, dot, suffix = ascii_filename.rpartition(".")
    if not dot:
        stem = ascii_filename
        suffix = ""

    normalized_stem = _FILENAME_SAFE_CHARS_PATTERN.sub("-", stem).strip("-")
    normalized_suffix = re.sub(r"[^a-z0-9]+", "", suffix)

    if not normalized_stem:
        normalized_stem = "file"

    if normalized_suffix:
        return f"{normalized_stem}.{normalized_suffix}"

    return normalized_stem


def build_storage_object_key(
    *,
    filename: str | None,
    namespace: str = "uploads",
) -> str:
    safe_filename = sanitize_storage_filename(filename)
    stem, dot, suffix = safe_filename.rpartition(".")
    if not dot:
        stem = safe_filename
        suffix = ""

    safe_namespace = _FILENAME_SAFE_CHARS_PATTERN.sub(
        "-", namespace.strip().lower()
    ).strip("-")
    safe_namespace = safe_namespace or "uploads"
    collision_suffix = str(uuid.uuid4()).split("-")[0]

    if suffix:
        return f"{safe_namespace}/{stem}-{collision_suffix}.{suffix}"

    return f"{safe_namespace}/{stem}-{collision_suffix}"


class S3:
    def __init__(
        self,
        s3_access_key_id: str,
        s3_secret_access_key: str,
        endpoint_url: str,
        region_name: str = "us-east-1",
    ) -> None:
        self.endpoint_url = endpoint_url
        self._session = aioboto3.Session(
            aws_access_key_id=s3_access_key_id,
            aws_secret_access_key=s3_secret_access_key,
            region_name=region_name,
        )

    async def create_bucket(self, bucket_name: str) -> None:
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
        ) as s3:
            existing_buckets = await s3.list_buckets()
            bucket_names = [b["Name"] for b in existing_buckets.get("Buckets", [])]

            if bucket_name not in bucket_names:
                await s3.create_bucket(Bucket=bucket_name)
                logger.info(f"Created S3 bucket: {bucket_name}")
            else:
                logger.info(f"S3 bucket already exists: {bucket_name}")

    async def put_bucket_lifecycle_configuration(
        self,
        bucket_name: str,
        rules: list[dict],
    ) -> None:
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
        ) as s3:
            existing_buckets = await s3.list_buckets()
            bucket_names = [b["Name"] for b in existing_buckets.get("Buckets", [])]

            if bucket_name not in bucket_names:
                raise ValueError(f"Bucket {bucket_name} does not exist.")

            await s3.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration={"Rules": rules},
            )

    async def upload_file(
        self,
        fileobj: BinaryIO | str,
        key: str,
        bucket_name: str,
        url_expiry: int = 3600,
        file_id: str | None = None,
    ) -> str:
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
        ) as s3:
            logger.info(
                "Uploading file to S3: bucket={bucket_name}, key={key}, file_id={file_id}".format(
                    bucket_name=bucket_name,
                    key=key,
                    file_id=file_id,
                )
            )

            extra_args = {}
            if file_id:
                extra_args["Metadata"] = {"file_id": file_id}

            try:
                if isinstance(fileobj, str):
                    await s3.upload_file(
                        Filename=fileobj,
                        Bucket=bucket_name,
                        Key=key,
                        ExtraArgs=extra_args if extra_args else None,
                    )
                elif hasattr(fileobj, "read"):
                    await s3.upload_fileobj(
                        Fileobj=fileobj,
                        Bucket=bucket_name,
                        Key=key,
                        ExtraArgs=extra_args if extra_args else None,
                    )
                else:
                    raise ValueError("fileobj must be a file path or a BinaryIO object")

                return await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": bucket_name, "Key": key},
                    ExpiresIn=url_expiry,
                )
            except StorageError:
                raise
            except Exception as error:
                raise StorageError("Failed to upload file to storage") from error

    async def upload_bytes(
        self,
        *,
        data: bytes,
        key: str,
        bucket_name: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
        ) as s3:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if metadata:
                extra_args["Metadata"] = metadata

            logger.info(
                "Uploading bytes to S3: bucket={bucket_name}, key={key}".format(
                    bucket_name=bucket_name,
                    key=key,
                )
            )
            try:
                await s3.upload_fileobj(
                    Fileobj=BytesIO(data),
                    Bucket=bucket_name,
                    Key=key,
                    ExtraArgs=extra_args if extra_args else None,
                )
            except StorageError:
                raise
            except Exception as error:
                raise StorageError("Failed to upload file bytes to storage") from error

        return StoredObject(
            bucket_name=bucket_name,
            key=key,
            content_type=content_type,
            size=len(data),
            metadata=metadata,
        )

    async def delete_file(
        self,
        key: str,
        bucket_name: str,
    ) -> None:
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
        ) as s3:
            logger.info(
                "Deleting file from S3: bucket={bucket_name}, key={key}".format(
                    bucket_name=bucket_name,
                    key=key,
                )
            )

            try:
                await s3.delete_object(
                    Bucket=bucket_name,
                    Key=key,
                )
            except StorageError:
                raise
            except Exception as error:
                raise StorageError("Failed to delete file from storage") from error

            logger.info(
                "File deleted from S3: bucket={bucket_name}, key={key}".format(
                    bucket_name=bucket_name,
                    key=key,
                )
            )

    async def generate_presigned_download_url(
        self,
        *,
        key: str,
        bucket_name: str,
        url_expiry: int = 3600,
    ) -> str:
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
        ) as s3:
            try:
                return await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": bucket_name, "Key": key},
                    ExpiresIn=url_expiry,
                )
            except StorageError:
                raise
            except Exception as error:
                raise StorageError("Failed to generate download URL") from error

    async def download_bytes(
        self,
        *,
        key: str,
        bucket_name: str,
    ) -> tuple[bytes, str | None]:
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
        ) as s3:
            logger.info(
                "Downloading file from S3: bucket={bucket_name}, key={key}".format(
                    bucket_name=bucket_name,
                    key=key,
                )
            )
            try:
                response = await s3.get_object(
                    Bucket=bucket_name,
                    Key=key,
                )
                body = await response["Body"].read()
            except StorageError:
                raise
            except Exception as error:
                raise StorageError("Failed to download file from storage") from error
            return body, response.get("ContentType")


def get_s3_client() -> S3:
    endpoint_url = CONFIG.MINIO_ENDPOINT
    if not endpoint_url.startswith(("http://", "https://")):
        endpoint_url = f"http://{endpoint_url}"

    return S3(
        s3_access_key_id=CONFIG.MINIO_ROOT_USER,
        s3_secret_access_key=CONFIG.MINIO_ROOT_PASSWORD,
        endpoint_url=endpoint_url,
    )


async def ensure_bucket_exists(bucket_name: str) -> None:
    client = get_s3_client()
    await client.create_bucket(bucket_name)
