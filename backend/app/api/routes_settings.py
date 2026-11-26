from fastapi import APIRouter, Depends
from backend.app.api.routes_auth import require_authenticated_user
from backend.app.core.config import settings
from backend.app.schemas.auth import User
from backend.app.schemas.settings import SystemSettingsSchema

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SystemSettingsSchema)
async def get_settings():
    """
    Get current RAG and system tuning parameters.
    """
    return SystemSettingsSchema(
        model_name=settings.DEFAULT_GEMINI_MODEL,
        temperature=settings.TEMPERATURE,
        chunk_size=settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP,
        retrieval_top_k=settings.DEFAULT_RETRIEVAL_TOP_K,
        rerank_top_n=settings.DEFAULT_RERANK_TOP_N,
        hybrid_alpha=settings.DEFAULT_HYBRID_ALPHA
    )


@router.post("", response_model=SystemSettingsSchema)
async def update_settings(
    new_settings: SystemSettingsSchema,
    current_user: User = Depends(require_authenticated_user)
):
    """
    Update runtime RAG tuning parameters (requires authenticated user).
    """
    settings.DEFAULT_GEMINI_MODEL = new_settings.model_name
    settings.TEMPERATURE = new_settings.temperature
    settings.DEFAULT_CHUNK_SIZE = new_settings.chunk_size
    settings.DEFAULT_CHUNK_OVERLAP = new_settings.chunk_overlap
    settings.DEFAULT_RETRIEVAL_TOP_K = new_settings.retrieval_top_k
    settings.DEFAULT_RERANK_TOP_N = new_settings.rerank_top_n
    settings.DEFAULT_HYBRID_ALPHA = new_settings.hybrid_alpha

    return new_settings
