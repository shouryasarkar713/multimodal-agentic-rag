from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
import uuid

class SessionCreate(BaseModel):
    title: Optional[str] = None

class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    message_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]

class CitationItem(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_number: int
    content_text: str

class MessageItem(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[CitationItem]] = None
    figure_refs: Optional[List[str]] = None  # List of figure image URLs
    confidence: Optional[float] = None
    created_at: datetime

class MessageListResponse(BaseModel):
    messages: List[MessageItem]

# Retrieve request and response schemas
class RetrieveRequest(BaseModel):
    query: str
    document_id: Optional[uuid.UUID] = None
    top_k: Optional[int] = 5

class RetrievedChunkItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content_type: str
    content_text: Optional[str] = None
    content_markdown: Optional[str] = None
    page_number: int
    section_title: Optional[str] = None
    image_url: Optional[str] = None

class RetrieveResponse(BaseModel):
    chunks: List[RetrievedChunkItem]
