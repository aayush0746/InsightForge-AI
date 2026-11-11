from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CitationInfo(BaseModel):
    source_filename: str
    page_number: int
    chunk_id: str
    snippet: str
    document_id: Optional[str] = None
    relevance_score: Optional[float] = None

class ThreadMessage(BaseModel):
    id: str
    role: str  # 'user' | 'assistant'
    content: str
    timestamp: str
    citations: Optional[List[CitationInfo]] = None
    is_grounded: Optional[bool] = None
    chart_data: Optional[Dict[str, Any]] = None

class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)

class ProjectThread(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[ThreadMessage] = []

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    color: Optional[str] = Field(default="indigo", max_length=30)
    icon: Optional[str] = Field(default="folder", max_length=30)
    document_ids: Optional[List[str]] = Field(default_factory=list)
    user_id: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    document_ids: Optional[List[str]] = None

class Project(BaseModel):
    id: str
    name: str
    description: str
    color: str
    icon: str
    document_ids: List[str] = []
    created_at: str
    updated_at: str
    thread_count: int = 0
    document_count: int = 0
    user_id: Optional[str] = None

class ThreadMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    enable_web_search: bool = False

