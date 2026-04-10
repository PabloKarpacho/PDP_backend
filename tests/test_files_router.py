import importlib
from io import BytesIO

import pytest
from fastapi import HTTPException

from src.config import CONFIG
from src.constants import Roles


files_router_module = importlib.import_module("src.routers.Files.router")
s3_db_module = importlib.import_module("src.database_control.s3.db")


class FakeLogger:
    def __init__(self) -> None:
        self.info_messages: list[tuple[str, dict | None]] = []
        self.error_messages: list[tuple[str, dict | None]] = []

    def info(self, message: str, extra: dict | None = None) -> None:
        self.info_messages.append((message, extra))

    def error(self, message: str, extra: dict | None = None) -> None:
        self.error_messages.append((message, extra))


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

    async def upload_fileobj(
        self,
        *,
        fileobj,
        key,
        bucket_name,
        content_type=None,
        metadata=None,
        size=None,
    ):
        data = fileobj.read()
        if hasattr(fileobj, "seek"):
            fileobj.seek(0)
        self.calls.append(
            {
                "data": data,
                "key": key,
                "bucket_name": bucket_name,
                "content_type": content_type,
                "metadata": metadata,
                "size": size,
            }
        )
        if self.error is not None:
            raise self.error
        return s3_db_module.StoredObject(
            bucket_name=bucket_name,
            key=key,
            content_type=content_type,
            size=size if size is not None else len(data),
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
        self.bytes_read = 0

    async def read(self, size: int = -1):
        chunk = self.file.read(size)
        self.bytes_read += len(chunk)
        return chunk


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
    fake_logger = FakeLogger()
    monkeypatch.setattr(files_router_module, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(files_router_module, "logger", fake_logger)
    upload = FakeUploadFile(filename="lesson.txt", content=b"payload")

    result = await files_router_module.upload_file(upload, user=build_user())

    assert result.success is True
    assert result.error is None
    assert result.meta.pagination is None
    assert result.data.download_url == "https://example.com/file"
    assert result.data.original_filename == "lesson.txt"
    assert result.data.content_type == "text/plain"
    assert result.data.size == 7
    assert not hasattr(result.data, "bucket_name")
    assert not hasattr(result.data, "key")
    assert fake_client.calls[0]["key"].startswith("uploads/user-1/")
    assert fake_client.calls == [
        {
            "data": b"payload",
            "key": fake_client.calls[0]["key"],
            "bucket_name": CONFIG.FILES_BUCKET_NAME,
            "content_type": "text/plain",
            "metadata": {"original_filename": "lesson.txt"},
            "size": 7,
        }
    ]
    assert fake_logger.info_messages[0] == (
        "File upload requested.",
        {"user_id": "user-1"},
    )
    assert fake_logger.info_messages[-1] == (
        "File upload succeeded.",
        {"user_id": "user-1", "content_type": "text/plain", "size": 7},
    )
    assert "download_url" not in str(fake_logger.info_messages)
    assert "bucket_name" not in str(fake_logger.info_messages)
    assert "uploads/user-1/" not in str(fake_logger.info_messages)


@pytest.mark.asyncio
async def test_upload_file_accepts_pdf_when_declared_type_matches_detected_type(
    monkeypatch,
):
    fake_client = FakeS3Client()
    monkeypatch.setattr(files_router_module, "get_s3_client", lambda: fake_client)

    upload = FakeUploadFile(
        filename="lesson.pdf",
        content=b"%PDF-1.7\n%test pdf",
        content_type="application/pdf",
    )

    result = await files_router_module.upload_file(upload, user=build_user())

    assert result.success is True
    assert result.data.content_type == "application/pdf"
    assert fake_client.calls[0]["key"].startswith("uploads/user-1/")
    assert fake_client.calls[0]["content_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_upload_file_rejects_oversized_payload(monkeypatch):
    monkeypatch.setattr(files_router_module.CONFIG, "FILE_UPLOAD_MAX_BYTES", 4)
    monkeypatch.setattr(files_router_module, "_UPLOAD_CHUNK_SIZE", 3)
    upload = FakeUploadFile(filename="lesson.txt", content=b"payload")

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "File is too large"
    assert upload.bytes_read == 6


@pytest.mark.asyncio
async def test_upload_file_rejects_application_octet_stream_declared_type(monkeypatch):
    upload = FakeUploadFile(
        filename="lesson.bin",
        content=b"%PDF-1.7\n%test pdf",
        content_type="application/octet-stream",
    )

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported file content type"


@pytest.mark.asyncio
async def test_upload_file_rejects_mismatched_declared_and_detected_content_type(
    monkeypatch,
):
    upload = FakeUploadFile(
        filename="lesson.txt",
        content=b"\x89PNG\r\n\x1a\nrest-of-png",
        content_type="text/plain",
    )

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Declared file content type does not match content"


@pytest.mark.asyncio
async def test_upload_file_rejects_binary_payload_declared_as_text_plain(monkeypatch):
    upload = FakeUploadFile(
        filename="lesson.txt",
        content=b"\x00\x01\x02\x03binary",
        content_type="text/plain",
    )

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported file content type"


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
    fake_logger = FakeLogger()
    monkeypatch.setattr(files_router_module, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(files_router_module, "logger", fake_logger)

    upload = FakeUploadFile(filename="lesson.txt", content=b"payload")

    with pytest.raises(HTTPException) as exc_info:
        await files_router_module.upload_file(upload, user=build_user())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "File upload failed"
    assert fake_logger.error_messages == [
        (
            "File upload failed due to storage backend error.",
            {
                "user_id": "user-1",
                "http_status_code": 500,
                "error_type": "storage_failure",
            },
        )
    ]
    assert "storage down" not in str(fake_logger.error_messages)
    assert "uploads/user-1/" not in str(fake_logger.error_messages)


def test_build_storage_object_key_is_user_scoped_and_adds_collision_safe_suffix(
    monkeypatch,
):
    monkeypatch.setattr(s3_db_module.uuid, "uuid4", lambda: "abc12345-fixed")

    key = s3_db_module.build_storage_object_key(
        filename="../../Lesson Plan 01!!.PDF",
        namespace="uploads",
        owner_scope="user-1",
    )

    assert key == "uploads/user-1/lesson-plan-01-abc12345.pdf"


def test_build_storage_object_key_uses_fallback_name_when_filename_is_empty(
    monkeypatch,
):
    monkeypatch.setattr(s3_db_module.uuid, "uuid4", lambda: "feedface-fixed")

    key = s3_db_module.build_storage_object_key(
        filename="   ",
        namespace="uploads",
        owner_scope="student-1",
    )

    assert key == "uploads/student-1/file-feedface"
