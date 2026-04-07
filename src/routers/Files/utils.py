from fastapi import HTTPException

from src.config import CONFIG
from src.database_control.s3 import sanitize_storage_filename


def normalize_content_type(content_type: str | None) -> str:
    """Normalize incoming content type to a predictable storage value."""
    normalized_content_type = (
        (content_type or "application/octet-stream").strip().lower()
    )
    return normalized_content_type or "application/octet-stream"


def validate_upload_metadata(
    *,
    filename: str | None,
    content_type: str,
) -> str:
    """Validate upload metadata that is known before streaming starts."""
    safe_filename = sanitize_storage_filename(filename)

    if content_type not in CONFIG.FILE_UPLOAD_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file content type")

    return safe_filename


def validate_upload_size(size: int) -> None:
    """Reject uploads that exceed the configured maximum size."""
    if size > CONFIG.FILE_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=400, detail="File is too large")
