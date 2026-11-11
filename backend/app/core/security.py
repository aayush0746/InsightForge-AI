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

def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename to prevent directory traversal
    and dangerous character sequences.
    """
    cleaned = os.path.basename(filename)
    cleaned = re.sub(r"[^\w\.\-\s]", "_", cleaned).strip()
    if not cleaned:
        cleaned = "unnamed_document.pdf"
    return cleaned

def validate_document_content(file_bytes: bytes, filename: str) -> None:
    """
    Ensure the uploaded file is within size limits and matches allowed extensions.
    """
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb} MB"
        )
    
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # If PDF, verify Magic Bytes '%PDF'
    if ext == ".pdf" and not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is not a valid PDF document (missing PDF magic header)."
        )

# Backward compatibility alias
validate_pdf_content = validate_document_content

def sanitize_text_input(user_query: str) -> str:
    """
    Detect and neutralize potential prompt injection vectors.
    Flags or strips malicious control commands.
    """
    query = user_query.strip()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Potential prompt injection detected in query: {query[:50]}")
            # Neutralize instruction override safely
            query = re.sub(pattern, "[sanitized-instruction]", query, flags=re.IGNORECASE)
    return query

