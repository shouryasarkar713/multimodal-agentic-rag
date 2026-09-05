import os
import uuid
import logging
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db, verify_api_key
from app.models.db import Session, Document, Message
from app.schemas.sessions import RetrieveRequest, RetrieveResponse, RetrievedChunkItem
from app.schemas.chat import ChatRequest, ChatResponse, CitationResponseItem, FigureRefResponseItem
from app.services.retrieval import retrieve_and_rerank
from app.agents.graph import compiled_graph

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

    # 2. Validate session exists
    session = await db.get(Session, body.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found"
        )

    # 3. Validate document_ids (Risk 8 & 404 validation)
    if body.document_ids:
        for doc_id in body.document_ids:
            doc = await db.get(Document, doc_id)
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {doc_id} not found"
                )
            if doc.status == "processing":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document '{doc.title or doc.filename}' is still being processed. Please wait for processing to complete."
                )

    # 4. Load past chat history in session (prior to this query)
    stmt_history = select(Message).where(Message.session_id == body.session_id).order_by(Message.created_at.asc())
    res_history = await db.execute(stmt_history)
    history_msgs = res_history.scalars().all()
    chat_history_list = [{"role": m.role, "content": m.content} for m in history_msgs]

    # 5. Persist user message row
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

    # 8. Run StateGraph invocation
    logging.info(
        f"[ChatAPI] Starting query execution for session={body.session_id}, "
        f"query='{body.query}', docs={body.document_ids}"
    )
    try:
        final_state = await compiled_graph.ainvoke(initial_state, config)
        logging.info(f"[ChatAPI] Query execution succeeded for session={body.session_id}")
    except Exception as e:
        import httpx
        import openai

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
        # If finalize node somehow didn't persist assistant message, fall back to final_state answer
        logging.warning("Assistant message not found in DB after finalize_node; constructing fallback message.")
        answer_text = final_state.get("generated_answer", "")
        citations_list = final_state.get("citations", [])
        figure_refs_list = final_state.get("figure_refs", [])
        confidence_val = final_state.get("confidence_score", 1.0)
    else:
        answer_text = asst_msg.content
        citations_list = asst_msg.citations or []
        figure_refs_list = asst_msg.figure_refs or []
        confidence_val = asst_msg.confidence_score if asst_msg.confidence_score is not None else 1.0

    # 10. Map Citations
    citation_items = []
    for c in citations_list:
        citation_items.append(CitationResponseItem(
            chunk_id=c.get("chunk_id") or uuid.uuid4(),
            document_id=c.get("document_id") or uuid.uuid4(),
            document_title=c.get("document_title"),
            filename=c.get("filename"),
            page_number=c.get("page_number", 1),
            section_title=c.get("section_title"),
            excerpt=c.get("excerpt", ""),
            relevance_score=c.get("relevance_score", 5.0)
        ))

    # 11. Map Figure References
    figure_ref_items = []
    for f in figure_refs_list:
        figure_ref_items.append(FigureRefResponseItem(
            chunk_id=f.get("chunk_id") or uuid.uuid4(),
            document_id=f.get("document_id") or uuid.uuid4(),
            image_path=f.get("image_path", ""),
            caption=f.get("caption", ""),
            page_number=f.get("page_number", 1)
        ))

    # 12. Return ChatResponse payload
    return ChatResponse(
        answer=answer_text,
        citations=citation_items,
        figure_refs=figure_ref_items,
        confidence_score=confidence_val,
        trace_id=trace_id
    )
