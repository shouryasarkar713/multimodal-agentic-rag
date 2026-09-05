import os
import uuid
import json
import logging
import httpx
import openai
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db
from app.models.db import Session, Message
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationResponseItem,
    FigureRefResponseItem
)
from app.schemas.sessions import RetrieveRequest, RetrieveResponse, RetrievedChunkItem
from app.services.retrieval import retrieve_and_rerank
from app.agents.graph import build_research_graph

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/retrieve", response_model=RetrieveResponse, status_code=status.HTTP_200_OK)
async def retrieve_endpoint(
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

@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit a query to the agentic RAG system and receive a citation-backed answer."""
    # 1. Validate query cannot be empty
    if not body.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )

    # 2. Check if session exists; auto-create if not found
    session = await db.get(Session, body.session_id)
    if not session:
        session = Session(
            id=body.session_id,
            title=body.query[:50]
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # 3. Retrieve recent conversation history for this session (up to 10 messages)
    stmt_history = (
        select(Message)
        .where(Message.session_id == body.session_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    res_history = await db.execute(stmt_history)
    history_messages = res_history.scalars().all()
    # Reverse to chronological order
    history_messages = list(reversed(history_messages))

    # 4. Format chat history
    chat_history_list = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ]

    # 5. Persist user query message in DB
    user_msg = Message(
        id=uuid.uuid4(),
        session_id=body.session_id,
        role="user",
        content=body.query
    )
    db.add(user_msg)
    session.updated_at = func.now()
    await db.commit()

    # 6. Initialize LangGraph State
    trace_id = uuid.uuid4()
    initial_state = {
        "user_query": body.query,
        "session_id": str(body.session_id),
        "chat_history": chat_history_list,
        "classified_intent": None,
        "parsed_query": None,
        "retrieval_types": [],
        "retrieved_chunks": [],
        "formatted_context": "",
        "retrieval_attempt": 0,
        "rewritten_query": None,
        "sub_queries": [],
        "sub_results": [],
        "evidence_scores": [],
        "evidence_sufficient": False,
        "generated_answer": "",
        "citations": [],
        "figure_refs": [],
        "confidence_score": 1.0,
        "validation_passed": None,
        "validation_issues": [],
        "trace_steps": [],
        "trace_id": str(trace_id)
    }

    # 7. Configure LangSmith Tracing
    langsmith_url = None
    if os.environ.get("LANGSMITH_API_KEY") and os.environ.get("LANGSMITH_PROJECT"):
        langsmith_url = f"https://smith.langchain.com/o/default/projects/p/{os.environ.get('LANGSMITH_PROJECT')}"

    config = {
        "configurable": {
            "db": db,
            "document_ids": body.document_ids,
            "langsmith_url": langsmith_url
        }
    }

    # 8. Execute Agentic Graph
    graph = build_research_graph()
    try:
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        is_timeout = False
        if isinstance(e, httpx.TimeoutException) or isinstance(e, openai.APITimeoutError):
            is_timeout = True
        elif "timeout" in str(e).lower() or "timed out" in str(e).lower():
            is_timeout = True

        if is_timeout:
            logging.error(f"LangGraph run timed out: {e}")
            await db.rollback()

            # Record QueryTrace with error step
            from app.models.db import QueryTrace
            error_trace = QueryTrace(
                id=trace_id,
                session_id=body.session_id,
                user_query=body.query,
                classified_intent="error",
                steps=[{
                    "step_name": "timeout_error",
                    "input_summary": body.query,
                    "output_summary": f"TimeoutException: {str(e)}",
                    "duration_ms": 30000,
                    "metadata": {"error": str(e)}
                }],
                total_duration_ms=30000,
                langsmith_url=None
            )
            db.add(error_trace)
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The AI service is slow. Please try again."
            )

        import traceback
        logging.error(f"LangGraph run failed with error: {e}\n{traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )

    # 9. Retrieve the finalized assistant reply message from DB
    stmt_asst = (
        select(Message)
        .where(Message.session_id == body.session_id, Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    res_asst = await db.execute(stmt_asst)
    asst_msg = res_asst.scalar_one_or_none()

    if not asst_msg:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent execution failed: assistant message was not created."
        )

    # 10. Parse citations and figures into schema formats
    citations_res = []
    for c in asst_msg.citations or []:
        citations_res.append(CitationResponseItem(
            chunk_id=uuid.UUID(str(c["chunk_id"])),
            document_id=uuid.UUID(str(c["document_id"])),
            document_title=c.get("document_title", "Unknown"),
            page_number=c["page_number"],
            section_title=c.get("section_title"),
            excerpt=c["excerpt"],
            relevance_score=c.get("relevance_score", 5.0),
            image_url=c.get("image_url")
        ))

    figure_refs_res = []
    for f in asst_msg.figure_refs or []:
        figure_refs_res.append(FigureRefResponseItem(
            chunk_id=uuid.UUID(str(f["chunk_id"])),
            document_id=uuid.UUID(str(f["document_id"])),
            image_path=f["image_path"],
            caption=f["caption"],
            page_number=f["page_number"]
        ))

    # Return structured Response
    confidence_val = asst_msg.confidence if asst_msg.confidence is not None else 1.0
    return ChatResponse(
        message_id=asst_msg.id,
        content=asst_msg.content,
        citations=citations_res,
        figure_refs=figure_refs_res,
        confidence=confidence_val,
        trace_id=uuid.UUID(str(state_val)) if (state_val := final_state.get("trace_id")) else trace_id,
        intent=final_state.get("classified_intent") or "paper_qa",
        retrieval_types=final_state.get("retrieval_types") or ["text"]
    )
