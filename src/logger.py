from contextvars import ContextVar
import logging
import re
from typing import Any

import graypy

from src.config import CONFIG


_SENSITIVE_FIELD_MARKERS = (
    "authorization",
    "token",
    "secret",
    "password",
    "cookie",
    "client_secret",
    "smtp_password",
    "bucket_name",
    "object_key",
    "storage_key",
    "download_url",
    "presigned_url",
)
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)(bearer\s+)[^\s\"']+")
_ASSIGNMENT_SECRET_PATTERN = re.compile(r"(?i)\b(password|secret|token)=([^\s&]+)")
_DSN_CREDENTIAL_PATTERN = re.compile(r"(://[^:/?#]+:)([^@]+)(@)")


def _is_sensitive_field(field_name: str | None) -> bool:
    if field_name is None:
        return False

    normalized_field_name = field_name.casefold()
    return any(marker in normalized_field_name for marker in _SENSITIVE_FIELD_MARKERS)


def _redact_string(value: str) -> str:
    redacted_value = _BEARER_TOKEN_PATTERN.sub(r"\1[REDACTED]", value)
    redacted_value = _ASSIGNMENT_SECRET_PATTERN.sub(r"\1=[REDACTED]", redacted_value)
    redacted_value = _DSN_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]\3", redacted_value)
    return redacted_value


def sanitize_log_data(value: Any, *, field_name: str | None = None) -> Any:
    if _is_sensitive_field(field_name):
        return "[REDACTED]"

    if isinstance(value, dict):
        return {
            key: sanitize_log_data(item, field_name=key) for key, item in value.items()
        }

    if isinstance(value, list):
        return [sanitize_log_data(item) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_log_data(item) for item in value)

    if isinstance(value, Exception):
        return _redact_string(str(value))

    if isinstance(value, str):
        return _redact_string(value)

    return value


class Logger:
    def __init__(self):
        self.logger = logging.getLogger("logger")
        self.logger.setLevel(logging.DEBUG)
        if not any(
            isinstance(handler, graypy.GELFUDPHandler)
            for handler in self.logger.handlers
        ):
            handler = graypy.GELFUDPHandler(CONFIG.GRAYLOG_HOST, CONFIG.GRAYLOG_PORT)
            self.logger.addHandler(handler)
        self._logs: ContextVar[tuple[str, ...]] = ContextVar("logger_logs", default=())
        self._extra: ContextVar[dict[str, Any]] = ContextVar("logger_extra", default={})
        self._context: ContextVar[dict[str, Any]] = ContextVar(
            "logger_context", default={}
        )

    def bind(self, **context: Any) -> None:
        current_context = dict(self._context.get())
        current_context.update(sanitize_log_data(context))
        self._context.set(current_context)

    def clear_context(self) -> None:
        self._logs.set(())
        self._extra.set({})
        self._context.set({})

    def error(self, record: str, extra: dict | None = None):
        self._append("ERROR", record, extra)

    def debug(self, record: str, extra: dict | None = None):
        self._append("DEBUG", record, extra)

    def info(self, record: str, extra: dict | None = None):
        self._append("INFO", record, extra)

    def _append(self, level: str, record: str, extra: dict | None = None) -> None:
        sanitized_record = sanitize_log_data(record)
        merged_extra = dict(self._context.get())
        if extra:
            merged_extra.update(sanitize_log_data(extra))

        formatted_record = self._format_record(level, sanitized_record, merged_extra)
        self._logs.set((*self._logs.get(), formatted_record))
        self._extra.set({**self._extra.get(), **merged_extra})

    def _format_record(
        self,
        level: str,
        record: str,
        extra: dict[str, Any],
    ) -> str:
        prefix_parts = [level]
        request_id = extra.get("request_id")
        if request_id:
            prefix_parts.append(f"request_id={request_id}")

        context_items = []
        for key in (
            "method",
            "path",
            "http_status_code",
            "time_taken",
            "error_type",
            "user_id",
        ):
            if key in extra:
                context_items.append(f"{key}={extra[key]}")

        formatted_context = f" | {' '.join(context_items)}" if context_items else ""
        return f"{' '.join(prefix_parts)} {record}{formatted_context}"

    def get_logs(self) -> str:
        return "\n".join(self._logs.get())

    def dump(self):
        log = self.get_logs()
        extra = dict(self._extra.get())
        self._logs.set(())
        self._extra.set({})

        if not log:
            return

        if CONFIG.SEND_LOGS_TO_GRAYLOG:
            payload = extra | {"env": CONFIG.ENV, "service": CONFIG.PROJECT_NAME}
            self.logger.info(log, extra=payload)
        else:
            print(log)


logger = Logger()
