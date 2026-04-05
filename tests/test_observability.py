from contextlib import asynccontextmanager
import importlib

from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request

from src.app import REQUEST_ID_HEADER, app
from src.logger import sanitize_log_data


app_module = importlib.import_module("src.app")


class FakeLogger:
    def __init__(self) -> None:
        self.current_context: dict = {}
        self.info_messages: list[tuple[str, dict | None]] = []
        self.error_messages: list[tuple[str, dict | None]] = []
        self.dump_calls = 0
        self.clear_context_calls = 0

    def bind(self, **context) -> None:
        self.current_context = {**self.current_context, **context}

    def clear_context(self) -> None:
        self.current_context = {}
        self.clear_context_calls += 1

    def info(self, message: str, extra: dict | None = None) -> None:
        merged_extra = {**self.current_context, **(extra or {})}
        self.info_messages.append((message, merged_extra))

    def error(self, message: str, extra: dict | None = None) -> None:
        merged_extra = {**self.current_context, **(extra or {})}
        self.error_messages.append((message, merged_extra))

    def dump(self) -> None:
        self.dump_calls += 1


def test_sanitize_log_data_redacts_sensitive_values():
    sanitized = sanitize_log_data(
        {
            "authorization": "Bearer secret-token",
            "nested": {"password": "plain-text"},
            "dsn": "postgresql://user:secret@localhost:5432/pdp",
        }
    )

    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["dsn"] == "postgresql://user:[REDACTED]@localhost:5432/pdp"


def test_middleware_propagates_request_id_to_response_and_logs(monkeypatch):
    fake_logger = FakeLogger()

    @asynccontextmanager
    async def noop_lifespan(_: object):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan
    monkeypatch.setattr(app_module, "logger", fake_logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/actuator/health/readiness",
                headers={REQUEST_ID_HEADER: "req-123"},
            )
    finally:
        app.router.lifespan_context = original_lifespan

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-123"
    assert fake_logger.info_messages[0][0] == "Request started."
    assert fake_logger.info_messages[0][1]["request_id"] == "req-123"
    assert fake_logger.info_messages[-1][0] == "Request completed."
    assert fake_logger.info_messages[-1][1]["path"] == "/actuator/health/readiness"
    assert fake_logger.info_messages[-1][1]["http_status_code"] == 200


@pytest.mark.asyncio
async def test_unexpected_exception_handler_logs_request_id():
    fake_logger = FakeLogger()
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "root_path": "",
            "app": app,
        }
    )
    request.state.request_id = "req-error"

    original_logger = app_module.logger
    app_module.logger = fake_logger
    try:
        response = await app_module.unexpected_exception_handler(
            request,
            RuntimeError("password=secret-value"),
        )
    finally:
        app_module.logger = original_logger

    assert response.status_code == 500
    assert response.headers[REQUEST_ID_HEADER] == "req-error"
    assert fake_logger.error_messages[0][0] == "Unhandled server error."
    assert fake_logger.error_messages[0][1]["request_id"] == "req-error"
    assert "secret-value" not in str(fake_logger.error_messages[0][1])
