import importlib
from io import BytesIO

import pytest

from src.config import CONFIG

files_router_module = importlib.import_module("src.routers.Files.router")


class FakeS3Client:
    def __init__(self):
        self.calls = []

    async def upload_file(self, *, fileobj, key, bucket_name):
        self.calls.append(
            {
                "fileobj": fileobj,
                "key": key,
                "bucket_name": bucket_name,
            }
        )
        return "https://example.com/file"


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


@pytest.mark.asyncio
async def test_upload_file_uses_async_s3_client(monkeypatch):
    fake_client = FakeS3Client()
    monkeypatch.setattr(files_router_module, "get_s3_client", lambda: fake_client)
    upload = FakeUploadFile(filename="lesson.txt", content=b"payload")

    result = await files_router_module.upload_file(upload)

    assert result == {"url": "https://example.com/file"}
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["key"] == "lesson.txt"
    assert fake_client.calls[0]["bucket_name"] == CONFIG.MINIO_FILES_BUCKET_NAME
    assert fake_client.calls[0]["fileobj"].read() == b"payload"
