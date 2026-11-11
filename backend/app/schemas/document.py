from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    file_size_bytes: int
    total_pages: int
    total_chunks: int
    upload_timestamp: datetime
    status: str = "indexed"  # processing, indexed, error
    error_message: Optional[str] = None
    user_id: Optional[str] = None

class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_filename: str
    page_number: int
    text: str
    word_count: int
    score: Optional[float] = None  # Similarity or rerank score

class DocumentUploadResponse(BaseModel):
    success: bool
    document: DocumentMetadata
    message: str

class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    total_count: int

