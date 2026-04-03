from fastapi import FastAPI
import pytest

from src import startup as startup_module


class FakeLogger:
    def __init__(self) -> None:
        self.info_messages: list[tuple[str, dict | None]] = []
        self.error_messages: list[tuple[str, dict | None]] = []
        self.dump_calls = 0

    def info(self, message: str, extra: dict | None = None) -> None:
        self.info_messages.append((message, extra))

    def error(self, message: str, extra: dict | None = None) -> None:
        self.error_messages.append((message, extra))

    def dump(self) -> None:
        self.dump_calls += 1


@pytest.mark.asyncio
async def test_ensure_minio_bucket_ready_logs_success(monkeypatch) -> None:
    fake_logger = FakeLogger()
    observed_buckets: list[str] = []

    async def fake_bucket_initializer(bucket_name: str) -> None:
        observed_buckets.append(bucket_name)

    monkeypatch.setattr(startup_module, "logger", fake_logger)

    await startup_module.ensure_minio_bucket_ready(
        bucket_name="pdp-files",
        bucket_initializer=fake_bucket_initializer,
        endpoint_url="http://minio:9000",
    )

    assert observed_buckets == ["pdp-files"]
    assert len(fake_logger.error_messages) == 0
    assert fake_logger.dump_calls == 1
    assert fake_logger.info_messages[0][0] == "Ensuring MinIO bucket exists."
    assert fake_logger.info_messages[1][0] == "MinIO bucket is ready."
    assert fake_logger.info_messages[0][1] == {
        "bucket_name": "pdp-files",
        "endpoint_url": "http://minio:9000",
    }


@pytest.mark.asyncio
async def test_ensure_minio_bucket_ready_raises_clear_error(monkeypatch) -> None:
    fake_logger = FakeLogger()

    async def failing_bucket_initializer(bucket_name: str) -> None:
        raise RuntimeError(f"cannot create {bucket_name}")

    monkeypatch.setattr(startup_module, "logger", fake_logger)

    with pytest.raises(RuntimeError, match="MinIO bucket initialization failed"):
        await startup_module.ensure_minio_bucket_ready(
            bucket_name="pdp-files",
            bucket_initializer=failing_bucket_initializer,
            endpoint_url="http://minio:9000",
        )

    assert fake_logger.dump_calls == 1
    assert len(fake_logger.error_messages) == 1
    assert fake_logger.error_messages[0][0] == "MinIO bucket initialization failed."
    assert fake_logger.error_messages[0][1] == {
        "bucket_name": "pdp-files",
        "endpoint_url": "http://minio:9000",
    }


@pytest.mark.asyncio
async def test_lifespan_runs_startup_successfully() -> None:
    events: list[str] = []

    async def fake_startup_runner() -> None:
        events.append("startup")

    app = FastAPI(lifespan=startup_module.create_lifespan(fake_startup_runner))

    async with app.router.lifespan_context(app):
        assert events == ["startup"]


@pytest.mark.asyncio
async def test_lifespan_propagates_startup_failure() -> None:
    async def failing_startup_runner() -> None:
        raise RuntimeError("startup failed")

    app = FastAPI(lifespan=startup_module.create_lifespan(failing_startup_runner))

    with pytest.raises(RuntimeError, match="startup failed"):
        async with app.router.lifespan_context(app):
            pass
