from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from backend.app.core.config import settings
from backend.app.core.gemini import gemini_client
from backend.app.rag.reranker import reranker
from backend.app.rag.vector_store import vector_store
from backend.app.schemas.settings import SystemHealthResponse
from backend.app.services.document_service import document_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=SystemHealthResponse)
async def health_check():
    """
    System status, storage, and embedding/reranker readiness.
    """
    try:
        total_docs = await run_in_threadpool(document_service.count_all_documents)
    except Exception:
        total_docs = 0
    try:
        total_chunks = await run_in_threadpool(vector_store.count)
    except Exception:
        total_chunks = 0

    return SystemHealthResponse(
        status="healthy",
        version=settings.VERSION,
        gemini_api_configured=gemini_client.is_configured,
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        cross_encoder_model=settings.CROSS_ENCODER_MODEL_NAME,
        reranker_active=reranker.is_enabled,
        chroma_db_status="connected",
        total_indexed_documents=total_docs,
        total_chunks=total_chunks
    )
