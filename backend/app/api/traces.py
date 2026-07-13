import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, verify_api_key
from app.models.db import QueryTrace

# Prefix configured as /traces to match /api/traces/{trace_id} contract
router = APIRouter(prefix="/traces", tags=["traces"], dependencies=[Depends(verify_api_key)])

@router.get("/{trace_id}", status_code=status.HTTP_200_OK)
async def get_query_trace(
    trace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed step-by-step query execution traces for a given trace_id."""
    trace = await db.get(QueryTrace, trace_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found"
        )
        
    return {
        "id": str(trace.id),
        "user_query": trace.user_query,
        "classified_intent": trace.classified_intent,
        "steps": trace.steps or [],
        "total_duration_ms": trace.total_duration_ms,
        "langsmith_url": trace.langsmith_url
    }
