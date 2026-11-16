from fastapi import APIRouter
from backend.app.schemas.settings import SystemHealthResponse
from backend.app.core.config import settings
from backend.app.rag.vector_store import vector_store
from backend.app.services.document_service import document_service

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=SystemHealthResponse)
async def health_check():
    """
    System status, storage, and embedding model readiness.
    """
    try:
        total_docs = len(document_service.list_documents())
    except Exception:
        total_docs = 0
    try:
        total_chunks = vector_store.count()
    except Exception:
        total_chunks = 0

    return SystemHealthResponse(
        status="healthy",
        version=settings.VERSION,
        gemini_api_configured=bool(settings.GEMINI_API_KEY),
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        cross_encoder_model=settings.CROSS_ENCODER_MODEL_NAME,
        chroma_db_status="connected",
        total_indexed_documents=total_docs,
        total_chunks=total_chunks
    )

