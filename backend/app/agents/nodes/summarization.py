import logging
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.agents.llm_factory import get_generation_llm
from app.config import settings
from app.models.db import Chunk, Document
from app.agents.state import AgentState
from app.agents.prompts import SUMMARIZATION_PROMPT

async def summarization_node(state: AgentState, config: dict) -> dict:
    """Summarize a specific section, figure, or document."""
    db: AsyncSession = config["configurable"]["db"]
    document_ids: Optional[List[Any]] = config["configurable"].get("document_ids")
    parsed_query = state.get("parsed_query") or {}
    
    section_ref = parsed_query.get("section_ref")
    figure_ref = parsed_query.get("figure_ref")
    
    start_time = time.time()
    
    # Resolve target document scope if not provided (Bug Fix)
    resolved_doc_ids = list(document_ids) if document_ids else []
    
    if not resolved_doc_ids:
        target_papers = parsed_query.get("target_papers") or []
        for paper_name in target_papers:
            if paper_name:
                stmt_find = select(Document.id).where(
                    or_(
                        Document.title.ilike(f"%{paper_name}%"),
                        Document.filename.ilike(f"%{paper_name}%")
                    )
                )
                res_find = await db.execute(stmt_find)
                found_ids = res_find.scalars().all()
                resolved_doc_ids.extend(found_ids)
                
        # If still empty, try matching parts of query/user_query to document titles
        if not resolved_doc_ids:
            user_query = state.get("user_query") or ""
            stmt_find = select(Document.id, Document.title, Document.filename)
            res_find = await db.execute(stmt_find)
            all_docs = res_find.all()
            for doc_id, doc_title, doc_filename in all_docs:
                title_clean = (doc_title or "").lower()
                fname_clean = (doc_filename or "").lower()
                query_words = [w.lower() for w in user_query.split() if len(w) > 3]
                if any((word in title_clean or word in fname_clean) for word in query_words):
                    resolved_doc_ids.append(doc_id)
                    break
                    
        # Fallback to the latest indexed document (excluding test.pdf)
        if not resolved_doc_ids:
            stmt_latest = select(Document.id).where(Document.filename != "test.pdf").order_by(Document.created_at.desc()).limit(1)
            res_latest = await db.execute(stmt_latest)
            latest_id = res_latest.scalar_one_or_none()
            if latest_id:
                resolved_doc_ids = [latest_id]
            else:
                stmt_any = select(Document.id).order_by(Document.created_at.desc()).limit(1)
                res_any = await db.execute(stmt_any)
                any_id = res_any.scalar_one_or_none()
                if any_id:
                    resolved_doc_ids = [any_id]
                    
    # 1. Retrieve target chunks
    stmt = select(Chunk)
    if resolved_doc_ids:
        stmt = stmt.where(Chunk.document_id.in_(resolved_doc_ids))
        
    target_desc = "entire paper"
    if section_ref:
        stmt = stmt.where(Chunk.section_title.ilike(f"%{section_ref}%"))
        target_desc = f"Section: {section_ref}"
    elif figure_ref:
        stmt = stmt.where(Chunk.content_type == "image").where(
            or_(
                Chunk.image_caption.ilike(f"%{figure_ref}%"),
                Chunk.content_text.ilike(f"%{figure_ref}%")
            )
        )
        target_desc = f"Figure: {figure_ref}"
    else:
        # Default to getting abstract or first page chunks
        stmt = stmt.where(Chunk.content_type.in_(["text", "table"])).order_by(Chunk.page_number.asc(), Chunk.chunk_index.asc()).limit(15)
        target_desc = "document summary"
        
    try:
        res = await db.execute(stmt)
        chunks = res.scalars().all()
        
        # If no chunks found, fall back to first few pages
        if not chunks:
            stmt_fallback = select(Chunk)
            if resolved_doc_ids:
                stmt_fallback = stmt_fallback.where(Chunk.document_id.in_(resolved_doc_ids))
            stmt_fallback = stmt_fallback.where(Chunk.content_type.in_(["text", "table"])).order_by(Chunk.page_number.asc(), Chunk.chunk_index.asc()).limit(10)
            res_fallback = await db.execute(stmt_fallback)
            chunks = res_fallback.scalars().all()
            
        # Format context
        context_parts = []
        for i, c in enumerate(chunks):
            content = c.content_text or c.content_markdown or c.image_caption or ""
            context_parts.append(f"[{i+1}] Page {c.page_number} ({c.section_title or 'General'}): {content}")
            
        context_str = "\n\n".join(context_parts)
        
        # 2. Call LLM to summarize
        prompt = SUMMARIZATION_PROMPT.format(
            context=context_str,
            target_description=target_desc
        )

        llm = get_generation_llm()
        response = await llm.ainvoke(prompt)
        answer = response.content.strip()
        
        # 3. Resolve Document Titles for citations
        all_doc_ids = list(set([c.document_id for c in chunks]))
        doc_titles = {}
        if all_doc_ids:
            stmt_titles = select(Document.id, Document.title, Document.filename).where(Document.id.in_(all_doc_ids))
            res_titles = await db.execute(stmt_titles)
            for d_id, d_title, d_fname in res_titles.all():
                doc_titles[d_id] = d_title or d_fname
                
        # 4. Build citations
        citations = []
        for c in chunks:
            citations.append({
                "chunk_id": str(c.id),
                "document_id": str(c.document_id),
                "document_title": doc_titles.get(c.document_id, "Unknown Document"),
                "page_number": c.page_number,
                "section_title": c.section_title or "General",
                "excerpt": (c.content_text or "")[:200],
                "relevance_score": 5.0
            })
            
        duration_ms = int((time.time() - start_time) * 1000)
        
        step = {
            "step_name": "summarization",
            "input_summary": f"Summarizing {target_desc}",
            "output_summary": f"Generated summary of length {len(answer)} chars using {len(chunks)} chunks.",
            "duration_ms": duration_ms,
            "metadata": {"chunks_count": len(chunks)}
        }
        
        return {
            "generated_answer": answer,
            "citations": citations,
            "confidence_score": 0.9,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in summarization_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "generated_answer": f"Failed to generate summary: {str(e)}",
            "citations": [],
            "confidence_score": 0.0,
            "trace_steps": (state.get("trace_steps") or []) + [{
                "step_name": "summarization",
                "input_summary": f"Summarizing {target_desc}",
                "output_summary": f"Failed: {str(e)}",
                "duration_ms": duration_ms,
                "metadata": {"error": str(e)}
            }]
        }
