from typing import List
from pydantic import BaseModel, Field

class SystemSettingsSchema(BaseModel):
    model_name: str
    temperature: float = Field(..., ge=0.0, le=2.0)
    chunk_size: int = Field(..., ge=20, le=1000)
    chunk_overlap: int = Field(..., ge=0, le=200)
    retrieval_top_k: int = Field(..., ge=1, le=50)
    rerank_top_n: int = Field(..., ge=1, le=20)
    hybrid_alpha: float = Field(..., ge=0.0, le=1.0)
    available_models: List[str] = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-2.5-pro",
    ]

class SystemHealthResponse(BaseModel):
    status: str
    version: str
    gemini_api_configured: bool
    embedding_model: str
    cross_encoder_model: str
    reranker_active: bool = False
    chroma_db_status: str
    total_indexed_documents: int
    total_chunks: int
