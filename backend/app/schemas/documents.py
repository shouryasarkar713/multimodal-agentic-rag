from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

class UploadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: str
    message: str

class DocumentItem(BaseModel):
    id: uuid.UUID
    filename: str
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    total_pages: int
    status: str
    created_at: datetime

class DocumentListResponse(BaseModel):
    documents: List[DocumentItem]

class ChunkCounts(BaseModel):
    text: int
    table: int
    image: int

class DocumentDetailResponse(BaseModel):
    id: uuid.UUID
    filename: str
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    total_pages: int
    status: str
    chunk_counts: ChunkCounts
    created_at: datetime

class DeleteResponse(BaseModel):
    message: str

class FigureItem(BaseModel):
    chunk_id: uuid.UUID
    page_number: int
    caption: Optional[str] = None
    image_url: str

class FiguresResponse(BaseModel):
    figures: List[FigureItem]
