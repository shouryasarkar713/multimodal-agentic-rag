import os
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, verify_api_key
from app.schemas.sessions import RetrieveRequest, RetrieveResponse, RetrievedChunkItem
from app.services.retrieval import retrieve_and_rerank

# Prefix configured as /chat to match /api/chat/retrieve contract
router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(verify_api_key)])

@router.post("/retrieve", response_model=RetrieveResponse, status_code=status.HTTP_200_OK)
async def retrieve_chunks(
    body: RetrieveRequest,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve and re-rank the most relevant document chunks (text, tables, and images) for a query."""
    top_k = body.top_k if body.top_k is not None else 5
    
    # Run the hybrid + multimodal retrieval and re-ranking pipeline
    ranked_chunks = await retrieve_and_rerank(
        session=db,
        query_text=body.query,
        document_id=body.document_id,
        top_k=top_k
    )
    
    chunk_items = []
    for c in ranked_chunks:
        # Determine image_url for image chunks
        image_url = None
        if c.content_type == "image" and c.image_path:
            filename = os.path.basename(c.image_path)
            image_url = f"/api/images/{filename}"
            
        chunk_items.append(RetrievedChunkItem(
            chunk_id=c.id,
            document_id=c.document_id,
            content_type=c.content_type,
            content_text=c.content_text,
            content_markdown=c.content_markdown,
            page_number=c.page_number,
            section_title=c.section_title,
            image_url=image_url
        ))
        
    return RetrieveResponse(chunks=chunk_items)
