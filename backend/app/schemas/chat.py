from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

class ChatRequest(BaseModel):
    session_id: uuid.UUID
    query: str
    document_ids: Optional[List[uuid.UUID]] = Field(default=None)

class CitationResponseItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int
    section_title: Optional[str] = None
    excerpt: str
    relevance_score: float

class FigureRefResponseItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    image_path: str
    caption: str
    page_number: int

class ChatResponse(BaseModel):
    message_id: uuid.UUID
    content: str
    citations: List[CitationResponseItem]
    figure_refs: List[FigureRefResponseItem]
    confidence: float
    trace_id: uuid.UUID
    intent: str
    retrieval_types: List[str]
