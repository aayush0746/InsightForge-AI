import re
import os
from pathlib import Path
from fastapi import HTTPException, status
from backend.app.core.config import settings
from backend.app.core.logger import logger

# Signatures for prompt injection detection
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"system\s*:\s*you\s+are\s+now",
    r"disregard\s+the\s+above",
    r"you\s+are\s+DAN",
    r"jailbreak",
    r"override\s+system\s+prompt",
    r"<\|\s*im_start\s*\|>",
    r"<\|\s*endoftext\s*\|>"
]

ZIP_OFFICE_EXTS = {".docx", ".pptx", ".xlsx"}
ZIP_MAGIC_PREFIXES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename to prevent directory traversal
    and dangerous character sequences.
    """
    cleaned = os.path.basename(filename or "")
    cleaned = re.sub(r"[^\w\.\-\s]", "_", cleaned).strip()
    if not cleaned:
        cleaned = "unnamed_document.txt"
    return cleaned


def validate_document_content(file_bytes: bytes, filename: str) -> None:
    """
    Ensure the uploaded file is non-empty, within size limits,
    matches allowed extensions, and passes magic-byte verification.
    """
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb} MB"
        )

    ext = Path(filename).suffix.lower()
    if not ext or ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext or '(none)'}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    if ext == ".pdf" and not file_bytes.lstrip().startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is not a valid PDF document (missing PDF magic header)."
        )

    if ext in ZIP_OFFICE_EXTS and not file_bytes.startswith(ZIP_MAGIC_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is not a valid {ext.upper()} archive (invalid ZIP header)."
        )

    if ext == ".png" and not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is not a valid PNG image."
        )

    if ext in {".jpg", ".jpeg"} and not file_bytes.startswith(b"\xff\xd8\xff"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is not a valid JPEG image."
        )

    if ext == ".webp" and not (len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is not a valid WebP image."
        )


# Backward compatibility alias
validate_pdf_content = validate_document_content


def sanitize_text_input(user_query: str) -> str:
    """
    Detect and neutralize potential prompt injection vectors.
    """
    query = (user_query or "").strip()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Potential prompt injection detected in query: {query[:50]}")
            query = re.sub(pattern, "[sanitized-instruction]", query, flags=re.IGNORECASE)
    return query
