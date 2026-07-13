import uuid
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
        if m.citations:
            for cit in m.citations:
                citations.append(CitationItem(
                    document_id=uuid.UUID(cit["document_id"]),
                    filename=cit["filename"],
                    page_number=cit["page_number"],
                    content_text=cit["content_text"]
                ))
                
        message_items.append(MessageItem(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=citations or None,
            figure_refs=m.figure_refs,
            confidence=m.confidence,
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
