from fastapi import HTTPException

from src.config import CONFIG
from src.database_control.s3 import sanitize_storage_filename

_PDF_SIGNATURE = b"%PDF-"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_WEBP_RIFF_SIGNATURE = b"RIFF"
_WEBP_FORMAT_SIGNATURE = b"WEBP"
_TEXT_WHITESPACE_BYTES = {9, 10, 12, 13}
_TEXT_PRINTABLE_MIN_RATIO = 0.95


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


def detect_content_type(sample: bytes) -> str | None:
    """Detect content type from a sample of the uploaded file bytes."""
    if sample.startswith(_PDF_SIGNATURE):
        return "application/pdf"

    if sample.startswith(_PNG_SIGNATURE):
        return "image/png"

    if sample.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"

    if (
        len(sample) >= 12
        and sample.startswith(_WEBP_RIFF_SIGNATURE)
        and sample[8:12] == _WEBP_FORMAT_SIGNATURE
    ):
        return "image/webp"

    if _looks_like_text_plain(sample):
        return "text/plain"

    return None


def validate_detected_content_type(
    *,
    declared_content_type: str,
    detected_content_type: str | None,
) -> str:
    """Validate that detected content matches the declared client MIME type."""
    if detected_content_type is None:
        raise HTTPException(status_code=400, detail="Unsupported file content type")

    if declared_content_type != detected_content_type:
        raise HTTPException(
            status_code=400,
            detail="Declared file content type does not match content",
        )

    return detected_content_type


def should_validate_content_sample(*, sample: bytes, reached_eof: bool) -> bool:
    """Decide when the current sample is sufficient for server-side validation."""
    if sample.startswith(_PDF_SIGNATURE):
        return True

    if sample.startswith(_PNG_SIGNATURE):
        return True

    if sample.startswith(_JPEG_SIGNATURE):
        return True

    if (
        len(sample) >= 12
        and sample.startswith(_WEBP_RIFF_SIGNATURE)
        and sample[8:12] == _WEBP_FORMAT_SIGNATURE
    ):
        return True

    if reached_eof:
        return True

    return len(sample) >= CONFIG.FILE_UPLOAD_SNIFF_BYTES


def _looks_like_text_plain(sample: bytes) -> bool:
    if not sample:
        return True

    if b"\x00" in sample:
        return False

    try:
        decoded = sample.decode("utf-8")
    except UnicodeDecodeError:
        return False

    if not decoded:
        return True

    printable_count = sum(
        1
        for char in decoded
        if char.isprintable() or ord(char) in _TEXT_WHITESPACE_BYTES
    )
    printable_ratio = printable_count / len(decoded)
    return printable_ratio >= _TEXT_PRINTABLE_MIN_RATIO
