import uuid
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db
from app.models.db import Session, Message
from app.schemas.sessions import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    MessageItem,
    MessageListResponse,
    CitationItem
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: Optional[SessionCreate] = None,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session."""
    title = body.title if (body and body.title) else "New Session"
    session = Session(title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        message_count=0,
        created_at=session.created_at,
        updated_at=session.updated_at
    )

@router.get("", response_model=SessionListResponse, status_code=status.HTTP_200_OK)
async def list_sessions(
    db: AsyncSession = Depends(get_db)
):
    """List all sessions ordered by updated_at descending with message counts."""
    # Subquery or count query for messages
    count_subq = (
        select(func.count(Message.id))
        .where(Message.session_id == Session.id)
        .scalar_subquery()
    )
    
    stmt = (
        select(Session, count_subq.label("msg_count"))
        .order_by(Session.updated_at.desc())
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    session_responses = []
    for session, msg_count in rows:
        session_responses.append(SessionResponse(
            id=session.id,
            title=session.title,
            message_count=msg_count or 0,
            created_at=session.created_at,
            updated_at=session.updated_at
        ))
        
    return SessionListResponse(sessions=session_responses)

@router.get("/{session_id}/messages", response_model=MessageListResponse, status_code=status.HTTP_200_OK)
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all messages for a session in chronological order."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    message_items = []
    for m in messages:
        # Safely extract citations
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
                    try:
                        chunk_id = cit.get("chunk_id")
                        if isinstance(chunk_id, str):
                            chunk_id = uuid.UUID(chunk_id)
                        doc_id = cit.get("document_id")
                        if isinstance(doc_id, str):
                            doc_id = uuid.UUID(doc_id)
                        citations.append(CitationItem(
                            chunk_id=chunk_id,
                            document_id=doc_id,
                            document_title=str(cit.get("document_title") or cit.get("filename") or "Document"),
                            page_number=int(cit.get("page_number") or 1),
                            section_title=cit.get("section_title"),
                            excerpt=str(cit.get("excerpt") or cit.get("content_text") or ""),
                            relevance_score=float(cit.get("relevance_score") or 5.0),
                            image_url=cit.get("image_url")
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
