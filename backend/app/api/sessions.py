import uuid
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db, verify_api_key
from app.models.db import Session, Message
from app.schemas.sessions import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    MessageListResponse,
    MessageItem,
    CitationItem
)

# Prefix configured as /sessions to match /api/sessions contract
router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: Optional[SessionCreate] = None,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session."""
    title = (body.title if body and body.title else "New Session").strip()
    if not title:
        title = "New Session"
        
    new_session = Session(title=title)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return SessionResponse(
        id=new_session.id,
        title=new_session.title,
        message_count=0,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at
    )

@router.get("", response_model=SessionListResponse)
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all chat sessions ordered by updated_at descending with message counts."""
    stmt = (
        select(Session, func.count(Message.id))
        .outerjoin(Message, Session.id == Message.session_id)
        .group_by(Session.id)
        .order_by(Session.updated_at.desc())
    )
    result = await db.execute(stmt)
    sessions_with_counts = result.all()
    
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                title=s.title,
                message_count=count,
                created_at=s.created_at,
                updated_at=s.updated_at
            ) for s, count in sessions_with_counts
        ]
    )

@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve message history for a specific chat session."""
    # Check if session exists
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    message_items = []
    for m in messages:
        # Cast citations from JSONB to CitationItem
        citations = []
        raw_citations = m.citations
        if raw_citations:
            if isinstance(raw_citations, str):
                try:
                    raw_citations = json.loads(raw_citations)
                except Exception:
                    raw_citations = []
            if isinstance(raw_citations, list):
                for cit in raw_citations:
                    if not isinstance(cit, dict):
                        continue
                    try:
                        raw_chunk_id = cit.get("chunk_id")
                        raw_doc_id = cit.get("document_id")
                        chunk_id = uuid.UUID(str(raw_chunk_id)) if raw_chunk_id else uuid.uuid4()
                        doc_id = uuid.UUID(str(raw_doc_id)) if raw_doc_id else uuid.uuid4()

                        citations.append(CitationItem(
                            chunk_id=chunk_id,
                            document_id=doc_id,
                            document_title=str(cit.get("document_title") or cit.get("filename") or "Document"),
                            page_number=int(cit.get("page_number") or 1),
                            section_title=cit.get("section_title"),
                            excerpt=str(cit.get("excerpt") or cit.get("content_text") or ""),
                            relevance_score=float(cit.get("relevance_score") or 5.0)
                        ))
                    except Exception as err:
                        logging.warning(f"Skipping malformed citation entry: {err}")

        # Safely extract figure_refs
        figure_refs = []
        raw_figures = m.figure_refs
        if raw_figures:
            if isinstance(raw_figures, str):
                try:
                    raw_figures = json.loads(raw_figures)
                except Exception:
                    raw_figures = []
            if isinstance(raw_figures, list):
                figure_refs = raw_figures

        message_items.append(MessageItem(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=citations if citations else None,
            figure_refs=figure_refs if figure_refs else None,
            confidence=m.confidence,
            trace_id=m.trace_id,
            created_at=m.created_at
        ))
        
    return MessageListResponse(messages=message_items)

@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session and all its associated messages."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    await db.delete(session)
    await db.commit()
    
    return {"message": "Session deleted successfully"}
