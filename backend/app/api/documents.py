import os
import uuid
import fitz  # PyMuPDF
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.dependencies import get_db, verify_api_key
from app.models.db import Document, Chunk
from app.schemas.documents import (
    UploadResponse,
    DocumentListResponse,
    DocumentItem,
    DocumentDetailResponse,
    ChunkCounts,
    DeleteResponse,
    FiguresResponse,
    FigureItem
)
from app.services.ingestion import run_ingestion_pipeline

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(verify_api_key)])

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a PDF document and start the background ingestion pipeline."""
    # 1. Validate file format
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
        
    # 2. Read contents to validate size and page count
    contents = await file.read()
    file_size = len(contents)
    
    # Check for empty file (Risk 9)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )
        
    # Check for file size > 50 MB (Risk 2)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 50 MB."
        )
        
    # 3. Check page count using PyMuPDF (Risk 2)
    try:
        doc_fitz = fitz.open(stream=contents, filetype="pdf")
        total_pages = len(doc_fitz)
        doc_fitz.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not open PDF. The file may be corrupted or password protected."
        )
        
    if total_pages > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum page limit of 100 pages."
        )
        
    # Check if a document with the same filename already exists
    stmt_check = select(Document).where(Document.filename == file.filename)
    result_check = await db.execute(stmt_check)
    existing_doc = result_check.scalars().first()
    if existing_doc:
        # Delete physical files from disk
        if os.path.exists(existing_doc.file_path):
            try:
                os.remove(existing_doc.file_path)
            except Exception as e:
                logging.error(f"Error removing PDF file {existing_doc.file_path}: {e}")
                
        # Fetch all image chunks to delete figure images
        stmt_img = select(Chunk.image_path).where(
            Chunk.document_id == existing_doc.id, 
            Chunk.content_type == "image"
        )
        res_img = await db.execute(stmt_img)
        img_paths = res_img.scalars().all()
        for path in img_paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logging.error(f"Error removing figure file {path}: {e}")
                    
        await db.delete(existing_doc)
        await db.commit()

    # 4. Save file to disk
    document_id = uuid.uuid4()
    os.makedirs("/data/uploads", exist_ok=True)
    file_path = f"/data/uploads/{document_id}.pdf"
    
    with open(file_path, "wb") as f:
        f.write(contents)
        
    # 5. Create Document row in DB
    new_doc = Document(
        id=document_id,
        filename=file.filename,
        total_pages=total_pages,
        file_path=file_path,
        file_size_bytes=file_size,
        status="processing"
    )
    
    db.add(new_doc)
    await db.commit()
    
    # 6. Enqueue background ingestion task
    background_tasks.add_task(run_ingestion_pipeline, document_id)
    
    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="processing",
        message="Document uploaded and processing started."
    )

@router.get("", response_model=DocumentListResponse)
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all uploaded documents."""
    stmt = select(Document).order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()
    
    return DocumentListResponse(
        documents=[
            DocumentItem(
                id=d.id,
                filename=d.filename,
                title=d.title,
                authors=d.authors,
                total_pages=d.total_pages,
                status=d.status,
                created_at=d.created_at
            ) for d in docs
        ]
    )

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get details and chunk summary for a specific document."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    # Count chunks grouped by content_type
    stmt = (
        select(Chunk.content_type, func.count(Chunk.id))
        .where(Chunk.document_id == document_id)
        .group_by(Chunk.content_type)
    )
    result = await db.execute(stmt)
    counts_map = {row[0]: row[1] for row in result.all()}
    
    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        title=doc.title,
        authors=doc.authors,
        total_pages=doc.total_pages,
        status=doc.status,
        created_at=doc.created_at,
        chunk_counts=ChunkCounts(
            text=counts_map.get("text", 0),
            table=counts_map.get("table", 0),
            image=counts_map.get("image", 0)
        )
    )

@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a document, its database records, chunks, embeddings and physical files."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    # 1. Delete physical files from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logging.error(f"Error removing PDF file {doc.file_path}: {e}")
            
    # Fetch all image chunks to delete figure images
    stmt = select(Chunk.image_path).where(
        Chunk.document_id == document_id, 
        Chunk.content_type == "image"
    )
    result = await db.execute(stmt)
    img_paths = result.scalars().all()
    
    for path in img_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logging.error(f"Error removing figure file {path}: {e}")
                
    # 2. Delete document row (cascades to chunks in DB)
    await db.delete(doc)
    await db.commit()
    
    return DeleteResponse(message="Document deleted successfully.")

@router.get("/{document_id}/figures", response_model=FiguresResponse)
async def get_document_figures(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List all extracted figures for a document."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id, Chunk.content_type == "image")
        .order_by(Chunk.chunk_index)
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    
    figures = []
    for c in chunks:
        filename = os.path.basename(c.image_path) if c.image_path else ""
        figures.append(FigureItem(
            chunk_id=c.id,
            page_number=c.page_number,
            caption=c.content_text,  # Returns the original extracted caption
            image_url=f"/api/images/{filename}"
        ))
        
    return FiguresResponse(figures=figures)

@router.post("/download_arxiv", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def download_arxiv(
    arxiv_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Download a PDF from arXiv by ID and start the ingestion pipeline."""
    import httpx
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    filename = f"{arxiv_id}.pdf"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, follow_redirects=True)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch PDF from arXiv: HTTP {res.status_code}"
                )
            contents = res.content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch PDF from arXiv: {str(e)}"
        )
        
    file_size = len(contents)
    
    try:
        doc_fitz = fitz.open(stream=contents, filetype="pdf")
        total_pages = len(doc_fitz)
        doc_fitz.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not open downloaded PDF."
        )
        
    # Check if a document with the same filename already exists
    stmt_check = select(Document).where(Document.filename == filename)
    result_check = await db.execute(stmt_check)
    existing_doc = result_check.scalars().first()
    if existing_doc:
        # Delete physical files from disk
        if os.path.exists(existing_doc.file_path):
            try:
                os.remove(existing_doc.file_path)
            except Exception as e:
                logging.error(f"Error removing PDF file {existing_doc.file_path}: {e}")
                
        # Fetch all image chunks to delete figure images
        stmt_img = select(Chunk.image_path).where(
            Chunk.document_id == existing_doc.id, 
            Chunk.content_type == "image"
        )
        res_img = await db.execute(stmt_img)
        img_paths = res_img.scalars().all()
        for path in img_paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logging.error(f"Error removing figure file {path}: {e}")
                    
        await db.delete(existing_doc)
        await db.commit()

    document_id = uuid.uuid4()
    os.makedirs("/data/uploads", exist_ok=True)
    file_path = f"/data/uploads/{document_id}.pdf"
    
    with open(file_path, "wb") as f:
        f.write(contents)
        
    new_doc = Document(
        id=document_id,
        filename=filename,
        total_pages=total_pages,
        file_path=file_path,
        file_size_bytes=file_size,
        status="processing"
    )
    
    db.add(new_doc)
    await db.commit()
    
    background_tasks.add_task(run_ingestion_pipeline, document_id)
    
    return UploadResponse(
        document_id=document_id,
        filename=filename,
        status="processing",
        message=f"ArXiv document {arxiv_id} downloaded and processing started."
    )
