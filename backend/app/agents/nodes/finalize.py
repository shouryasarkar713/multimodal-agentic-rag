import uuid
import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Message, QueryTrace
from app.agents.state import AgentState

async def finalize_node(state: AgentState, config: dict) -> dict:
    """Save the final generated answer message and query trace log to the database."""
    db: AsyncSession = config["configurable"]["db"]
    
    session_id = state.get("session_id")
    trace_id = state.get("trace_id")
    
    # Estimate final total duration
    trace_steps = state.get("trace_steps") or []
    total_duration_ms = sum(step.get("duration_ms", 0) for step in trace_steps)
    
    try:
        # 1. Create and persist Message row for the assistant's reply
        new_msg = Message(
            id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            role="assistant",
            content=state.get("generated_answer", ""),
            citations=state.get("citations") or [],
            figure_refs=state.get("figure_refs") or [],
            confidence=state.get("confidence_score", 0.0),
            trace_id=uuid.UUID(trace_id)
        )
        db.add(new_msg)
        
        # 2. Create and persist QueryTrace row
        new_trace = QueryTrace(
            id=uuid.UUID(trace_id),
            session_id=uuid.UUID(session_id),
            user_query=state.get("user_query", ""),
            classified_intent=state.get("classified_intent", "paper_qa"),
            steps=trace_steps,
            total_duration_ms=total_duration_ms,
            langsmith_url=config["configurable"].get("langsmith_url")
        )
        db.add(new_trace)
        
        # Commit transaction
        await db.commit()
        logging.info(f"Saved assistant message and trace_id {trace_id} successfully.")
        
    except Exception as e:
        logging.error(f"Error in finalize_node during database commit: {e}")
        await db.rollback()
        
    return {}
