import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.api.routes_auth import get_effective_owner_id
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.schemas.document import (
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentListResponse
)
from backend.app.services.document_service import document_service, SHARED_USER_ID

router = APIRouter(prefix="/documents", tags=["Documents"])

MIME_TYPES_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".xml": "application/xml",
    ".rtf": "application/rtf",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class UrlIngestRequest(BaseModel):
    url: str


class DocumentCompareRequest(BaseModel):
    doc_id_1: str
    doc_id_2: str


@router.post("/url", response_model=DocumentUploadResponse)
async def ingest_url(
    request: UrlIngestRequest,
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Safely scrape and index a public webpage URL into ChromaDB.
    """
    if not request.url.startswith("http://") and not request.url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )
    try:
        doc_meta = await run_in_threadpool(document_service.upload_url, request.url, owner_id)
        return DocumentUploadResponse(
            success=True,
            document=doc_meta,
            message=f"Webpage '{request.url}' successfully scraped and indexed ({doc_meta.total_chunks} chunks)."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL ingest failed for {request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape & index URL: {str(e)}"
        )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Upload and index a document across all supported formats into ChromaDB.
    """
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if not ext or ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{ext or '(none)'}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    try:
        content = await file.read()
        doc_meta = await run_in_threadpool(
            document_service.upload_document,
            content,
            filename,
            owner_id
        )
        return DocumentUploadResponse(
            success=True,
            document=doc_meta,
            message=f"Document '{filename}' processed and indexed successfully."
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed for {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(owner_id: str = Depends(get_effective_owner_id)):
    """
    List all documents accessible to this authenticated user or isolated guest session.
    """
    docs = await run_in_threadpool(document_service.list_documents, owner_id)
    return DocumentListResponse(
        documents=docs,
        total_count=len(docs)
    )


@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(
    document_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    doc = await run_in_threadpool(document_service.get_document, document_id, owner_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or access denied."
        )
    return doc


@router.get("/{document_id}/preview")
async def get_document_preview(
    document_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Returns extracted page/slide/sheet/structured text sections for inline previewing
    of any supported document format or scraped URL.
    """
    preview = await run_in_threadpool(document_service.get_document_preview, document_id, owner_id)
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview for document '{document_id}' not found or access denied."
        )
    return preview


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Serve raw document file for browser inline viewing or download with strict MIME typing.
    """
    file_path = await run_in_threadpool(document_service.get_document_file_path, document_id, owner_id)
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File for document '{document_id}' not found or access denied."
        )

    ext = file_path.suffix.lower()
    guessed, _ = mimetypes.guess_type(str(file_path))
    media_type = MIME_TYPES_BY_EXT.get(ext) or guessed or "application/octet-stream"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        content_disposition_type="inline"
    )


@router.delete("/guest/clear")
async def clear_guest_documents(owner_id: str = Depends(get_effective_owner_id)):
    """
    Purges temporary documents uploaded by the caller's guest session.
    """
    if not owner_id.startswith("guest_"):
        return {"success": True, "purged_count": 0}
    purged = await run_in_threadpool(document_service.clear_guest_data, owner_id)
    return {"success": True, "purged_count": purged}


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Delete a document owned by the caller and purge its embeddings.
    """
    doc = await run_in_threadpool(document_service.get_document, document_id, owner_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )

    if doc.user_id == SHARED_USER_ID or doc.user_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only delete your own uploaded documents."
        )

    success = await run_in_threadpool(document_service.delete_document, document_id, owner_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or could not be deleted."
        )
    return {"success": True, "message": f"Document '{document_id}' deleted successfully."}


@router.post("/compare")
async def compare_documents(
    request: DocumentCompareRequest,
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Perform deep comparative matrix analysis between two accessible documents.
    """
    try:
        doc1 = await run_in_threadpool(document_service.get_document, request.doc_id_1, owner_id)
        doc2 = await run_in_threadpool(document_service.get_document, request.doc_id_2, owner_id)
        if not doc1 or not doc2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both documents not found or access denied."
            )
        comparison = await run_in_threadpool(
            document_service.compare_documents,
            request.doc_id_1,
            request.doc_id_2,
            owner_id
        )
        return {"success": True, "data": comparison}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Document comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Comparison failed: {str(e)}"
        )
