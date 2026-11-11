from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Citation(BaseModel):
    source_filename: str
    page_number: int
    chunk_id: str
    snippet: str
    document_id: Optional[str] = None
    relevance_score: Optional[float] = None

class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000, description="User question to answer")
    document_ids: Optional[List[str]] = Field(default=None, description="Filter search to specific documents")
    use_reranker: bool = Field(default=True, description="Enable CrossEncoder reranking")
    enable_web_search: bool = Field(default=False, description="Enable live web search augmentation")
    top_k: Optional[int] = Field(default=None, description="Number of candidate chunks to retrieve")
    top_n: Optional[int] = Field(default=None, description="Number of reranked chunks to use for context")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Conversation history turns")

class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    retrieved_chunks_count: int
    reranked_chunks_count: int
    is_grounded: bool
    unanswered_reason: Optional[str] = None
    chart_data: Optional[Dict[str, Any]] = None
