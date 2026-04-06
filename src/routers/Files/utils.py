from fastapi import HTTPException

from src.config import CONFIG
from src.database_control.s3 import sanitize_storage_filename


def normalize_content_type(content_type: str | None) -> str:
    """Normalize incoming content type to a predictable storage value."""
    normalized_content_type = (
        (content_type or "application/octet-stream").strip().lower()
    )
    return normalized_content_type or "application/octet-stream"


def validate_upload_input(
    *,
    filename: str | None,
    content_type: str,
    size: int,
) -> str:
    """Validate upload boundary inputs and return a safe filename."""
    safe_filename = sanitize_storage_filename(filename)

    if size > CONFIG.FILE_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=400, detail="File is too large")

    if content_type not in CONFIG.FILE_UPLOAD_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file content type")

    return safe_filename
