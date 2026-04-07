import importlib
from io import BytesIO

import pytest

s3_db_module = importlib.import_module("src.database_control.s3.db")


def test_get_s3_client_uses_iam_role_chain_for_aws_backend(monkeypatch) -> None:
    observed_session_kwargs: list[dict] = []

    class FakeSession:
        def __init__(self, **kwargs) -> None:
            observed_session_kwargs.append(kwargs)

    monkeypatch.setattr(s3_db_module.aioboto3, "Session", FakeSession)
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_BACKEND", "aws")
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_REGION", "eu-central-1")

    client = s3_db_module.get_s3_client()

    assert client.endpoint_url is None
    assert observed_session_kwargs == [{"region_name": "eu-central-1"}]


def test_get_s3_client_uses_minio_credentials_and_endpoint(monkeypatch) -> None:
    observed_session_kwargs: list[dict] = []

    class FakeSession:
        def __init__(self, **kwargs) -> None:
            observed_session_kwargs.append(kwargs)

    monkeypatch.setattr(s3_db_module.aioboto3, "Session", FakeSession)
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_BACKEND", "minio")
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_REGION", "us-east-1")
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_SECURE", True)
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_ROOT_USER", "minio-user")
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_ROOT_PASSWORD", "minio-pass")

    client = s3_db_module.get_s3_client()

    assert client.endpoint_url == "https://minio:9000"
    assert observed_session_kwargs == [
        {
            "aws_access_key_id": "minio-user",
            "aws_secret_access_key": "minio-pass",
            "region_name": "us-east-1",
        }
    ]


@pytest.mark.asyncio
async def test_upload_fileobj_streams_existing_file_object(monkeypatch) -> None:
    observed_calls: list[dict] = []

    class FakeS3Client:
        async def upload_fileobj(self, *, Fileobj, Bucket, Key, ExtraArgs=None):
            observed_calls.append(
                {
                    "fileobj": Fileobj,
                    "bucket": Bucket,
                    "key": Key,
                    "extra_args": ExtraArgs,
                }
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def client(self, service_name, **kwargs):
            assert service_name == "s3"
            return FakeS3Client()

    monkeypatch.setattr(
        s3_db_module.aioboto3, "Session", lambda **kwargs: FakeSession()
    )

    client = s3_db_module.S3(region_name="us-east-1")
    fileobj = BytesIO(b"payload")

    stored_object = await client.upload_fileobj(
        fileobj=fileobj,
        key="uploads/test.txt",
        bucket_name="files",
        content_type="text/plain",
        metadata={"original_filename": "lesson.txt"},
        size=7,
    )

    assert observed_calls == [
        {
            "fileobj": fileobj,
            "bucket": "files",
            "key": "uploads/test.txt",
            "extra_args": {
                "ContentType": "text/plain",
                "Metadata": {"original_filename": "lesson.txt"},
            },
        }
    ]
    assert stored_object.bucket_name == "files"
    assert stored_object.key == "uploads/test.txt"
    assert stored_object.content_type == "text/plain"
    assert stored_object.size == 7
