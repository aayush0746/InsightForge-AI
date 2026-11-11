from typing import Optional, List
from pydantic import BaseModel

class SystemSettingsSchema(BaseModel):
    model_name: str
    temperature: float
    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int
    rerank_top_n: int
    hybrid_alpha: float
    available_models: List[str] = [
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-pro-latest",
        "gemini-2.5-pro",
        "gemini-flash-latest"
    ]

class SystemHealthResponse(BaseModel):
    status: str
    version: str
    gemini_api_configured: bool
    embedding_model: str
    cross_encoder_model: str
    chroma_db_status: str
    total_indexed_documents: int
    total_chunks: int

