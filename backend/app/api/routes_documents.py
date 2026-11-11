from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import FileResponse
from backend.app.schemas.document import (
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentListResponse
)
from backend.app.services.document_service import document_service
from backend.app.api.routes_auth import get_current_user_optional
from backend.app.schemas.auth import User
from backend.app.core.config import settings
from backend.app.core.logger import logger

router = APIRouter(prefix="/documents", tags=["Documents"])

class UrlIngestRequest(BaseModel):
    url: str

class DocumentCompareRequest(BaseModel):
    doc_id_1: str
    doc_id_2: str

@router.post("/url", response_model=DocumentUploadResponse)
async def ingest_url(
    request: UrlIngestRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Ingest and index a live web page URL into ChromaDB.
    """
    if not request.url.startswith("http://") and not request.url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )
    try:
        user_id = current_user.id if current_user else None
        doc_meta = document_service.upload_url(request.url, user_id=user_id)
        return DocumentUploadResponse(
            success=True,
            document=doc_meta,
            message=f"Webpage '{request.url}' successfully scraped and indexed ({doc_meta.total_chunks} chunks)."
        )
    except Exception as e:
        logger.error(f"URL ingest failed for {request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape & index URL: {str(e)}"
        )

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Upload and index a document (PDF, DOCX, TXT, MD, CSV) into ChromaDB.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    try:
        content = await file.read()
        user_id = current_user.id if current_user else None
        doc_meta = document_service.upload_document(
            file_bytes=content,
            original_filename=file.filename,
            user_id=user_id
        )
        return DocumentUploadResponse(
            success=True,
            document=doc_meta,
            message=f"Document '{file.filename}' processed and indexed successfully."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List all uploaded and indexed documents.
    """
    user_id = current_user.id if current_user else None
    docs = document_service.list_documents(user_id=user_id)
    return DocumentListResponse(
        documents=docs,
        total_count=len(docs)
    )

@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get detailed metadata for a specific document.
    """
    user_id = current_user.id if current_user else None
    doc = document_service.get_document(document_id, user_id=user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or access denied."
        )
    return doc

@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Serve raw document file for browser inline viewing (e.g. split-screen PDF viewer).
    """
    user_id = current_user.id if current_user else None
    file_path = document_service.get_document_file_path(document_id, user_id=user_id)
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File for document '{document_id}' not found or access denied."
        )

    ext = file_path.suffix.lower()
    media_type = "application/pdf" if ext == ".pdf" else "text/plain"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        content_disposition_type="inline"
    )

@router.delete("/guest/clear")
async def clear_guest_documents():
    """
    Purge all temporary documents uploaded by guests.
    """
    purged = document_service.clear_guest_data()
    return {"success": True, "purged_count": purged}

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Delete a document and its embeddings from the vector store and Supabase Cloud.
    """
    user_id = current_user.id if current_user else None
    doc = document_service.get_document(document_id, user_id=user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )

    # User isolation check
    if current_user and doc.user_id and doc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only delete your own documents."
        )

    success = document_service.delete_document(document_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or could not be deleted."
        )
    return {"success": True, "message": f"Document '{document_id}' deleted successfully."}

@router.post("/compare")
async def compare_documents(request: DocumentCompareRequest):
    """
    Perform deep AI comparison matrix between two uploaded documents.
    """
    try:
        comparison = document_service.compare_documents(request.doc_id_1, request.doc_id_2)
        return {"success": True, "data": comparison}
    except Exception as e:
        logger.error(f"Document comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Comparison failed: {str(e)}"
        )
