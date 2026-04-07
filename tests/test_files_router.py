import importlib
from io import BytesIO

import pytest
from fastapi import HTTPException

from src.config import CONFIG
from src.constants import Roles


files_router_module = importlib.import_module("src.routers.Files.router")
s3_db_module = importlib.import_module("src.database_control.s3.db")


class FakeS3Client:
    def __init__(self, *, response=None, error: Exception | None = None):
        self.calls = []
        self.response = response or {
            "url": "https://example.com/file",
            "key": "uploads/2026/04/05/test-file.txt",
            "bucket_name": CONFIG.FILES_BUCKET_NAME,
            "content_type": "text/plain",
            "size": 7,
            "original_filename": "lesson.txt",
        }
        self.error = error

    async def upload_bytes(
        self,
        *,
        data,
        key,
        bucket_name,
        content_type=None,
        metadata=None,
    ):
        self.calls.append(
            {
                "data": data,
                "key": key,
                "bucket_name": bucket_name,
                "content_type": content_type,
                "metadata": metadata,
            }
        )
        if self.error is not None:
            raise self.error
        return s3_db_module.StoredObject(
            bucket_name=bucket_name,
            key=key,
            content_type=content_type,
            size=len(data),
            metadata=metadata,
        )

    async def generate_presigned_download_url(
        self, *, key, bucket_name, url_expiry=3600
    ):
        return self.response["url"]


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes, content_type: str = "text/plain"):
        self.filename = filename
        self.content_type = content_type
        self.file = BytesIO(content)

    async def read(self):
        self.file.seek(0)
        return self.file.read()


def build_user():
    return type(
        "User",
        (),
        {
            "id": "user-1",
            "role": Roles.TEACHER,
        },
    )()


@pytest.mark.asyncio
async def test_upload_file_returns_structured_file_metadata(monkeypatch):
    fake_client = FakeS3Client()
    monkeypatch.setattr(files_router_module, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(
        files_router_module, "build_storage_object_key", lambda **kwargs: "safe/key.txt"
    )

    upload = FakeUploadFile(filename="lesson.txt", content=b"payload")

    result = await files_router_module.upload_file(upload, user=build_user())

    assert result.success is True
    assert result.error is None
    assert result.meta.pagination is None
    assert result.data.download_url == "https://example.com/file"
    assert result.data.original_filename == "lesson.txt"
    assert result.data.content_type == "text/plain"
    assert result.data.size == 7
    assert fake_client.calls == [
        {
            "data": b"payload",
            "key": "safe/key.txt",
            "bucket_name": CONFIG.FILES_BUCKET_NAME,
            "content_type": "text/plain",
            "metadata": {"original_filename": "lesson.txt"},
        }
    ]


@pytest.mark.asyncio
async def test_upload_file_rejects_oversized_payload(monkeypatch):
    monkeypatch.setattr(files_router_module.CONFIG, "FILE_UPLOAD_MAX_BYTES", 4)
    upload = FakeUploadFile(filename="lesson.txt", content=b"payload")

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "File is too large"


@pytest.mark.asyncio
async def test_upload_file_rejects_disallowed_content_type(monkeypatch):
    monkeypatch.setattr(
        files_router_module.CONFIG,
        "FILE_UPLOAD_ALLOWED_CONTENT_TYPES",
        ("text/plain",),
    )
    upload = FakeUploadFile(
        filename="lesson.pdf",
        content=b"payload",
        content_type="application/pdf",
    )

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported file content type"


@pytest.mark.asyncio
async def test_upload_file_normalizes_storage_errors(monkeypatch):
    fake_client = FakeS3Client(error=s3_db_module.StorageError("storage down"))
    monkeypatch.setattr(files_router_module, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(
        files_router_module, "build_storage_object_key", lambda **kwargs: "safe/key.txt"
    )

    upload = FakeUploadFile(filename="lesson.txt", content=b"payload")

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "File upload failed"


def test_build_storage_object_key_sanitizes_name_and_adds_collision_safe_suffix(
    monkeypatch,
):
    monkeypatch.setattr(s3_db_module.uuid, "uuid4", lambda: "abc12345-fixed")

    key = s3_db_module.build_storage_object_key(
        filename="../../Lesson Plan 01!!.PDF",
        namespace="homework",
    )

    assert key == "homework/lesson-plan-01-abc12345.pdf"


def test_build_storage_object_key_uses_fallback_name_when_filename_is_empty(
    monkeypatch,
):
    monkeypatch.setattr(s3_db_module.uuid, "uuid4", lambda: "feedface-fixed")

    key = s3_db_module.build_storage_object_key(
        filename="   ",
        namespace="chat",
    )

    assert key == "chat/file-feedface"
