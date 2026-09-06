import uuid
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.agents.state import AgentState
from app.models.db import Chunk, Document
from app.services.retrieval import retrieve_and_rerank

async def retrieval_orchestrator_node(state: AgentState, config: dict) -> dict:
    """Orchestrates dense, sparse, CLIP image, and metadata searches."""
    db: AsyncSession = config["configurable"]["db"]
    document_ids: Optional[List[uuid.UUID]] = config["configurable"].get("document_ids")
    
    query_text = state.get("rewritten_query") or state.get("parsed_query", {}).get("query_text") or state.get("user_query")
    retrieval_types = list(state.get("retrieval_types") or ["text"])
    
    # Auto-resolve target_papers → document_ids when no explicit scope is provided (Bug 1: Home page global search)
    if not document_ids:
        target_papers = (state.get("parsed_query") or {}).get("target_papers") or []
        if target_papers:
            resolved_ids = []
            for paper_name in target_papers:
                if paper_name and len(paper_name) > 3:
                    stmt_resolve = select(Document.id).where(
                        or_(
                            Document.title.ilike(f"%{paper_name}%"),
                            Document.filename.ilike(f"%{paper_name}%")
                        )
                    )
                    res_resolve = await db.execute(stmt_resolve)
                    found = res_resolve.scalars().all()
                    resolved_ids.extend(found)
            if resolved_ids:
                document_ids = list(set(resolved_ids))
                logging.info(f"[RetrievalOrchestrator] Resolved target_papers={target_papers} → document_ids={document_ids}")
        
        # If still no document_ids and query text mentions a specific paper title,
        # do a fuzzy match across all document titles
        if not document_ids and query_text:
            stmt_all = select(Document.id, Document.title, Document.filename)
            res_all = await db.execute(stmt_all)
            all_docs = res_all.all()
            query_words = [w.lower() for w in (query_text or "").split() if len(w) > 4]
            for doc_id, doc_title, doc_fname in all_docs:
                title_lower = (doc_title or "").lower()
                fname_lower = (doc_fname or "").lower()
                if any(word in title_lower or word in fname_lower for word in query_words):
                    if not document_ids:
                        document_ids = []
                    document_ids.append(doc_id)
                    logging.info(f"[RetrievalOrchestrator] Fuzzy matched query to document: '{doc_title or doc_fname}'")

    # Auto-expand retrieval to include images if query touches visual, architectural, or structural concepts
    visual_keywords = ["attention", "architecture", "mechanism", "figure", "diagram", "model", "layer", "transformer", "network", "overview", "structure", "dimension"]
    if any(k in query_text.lower() for k in visual_keywords) and "image" not in retrieval_types:
        retrieval_types.append("image")
        logging.info("[RetrievalOrchestrator] Auto-expanded retrieval to include images")
    
    start_time = time.time()
    
    try:
        # Run unified retrieve_and_rerank service (handles dense + sparse + CLIP + metadata)
        ranked_chunks = await retrieve_and_rerank(
            session=db,
            query_text=query_text,
            document_id=document_ids[0] if document_ids and len(document_ids) == 1 else None,
            document_ids=document_ids if document_ids and len(document_ids) > 1 else None,
            content_types=retrieval_types,
            top_k=20
        )
        
        # Serialize chunks to dicts for graph state
        chunk_dicts = []
        for c in ranked_chunks:
            chunk_dict = {
                "id": str(c.id),
                "document_id": str(c.document_id),
                "content_type": c.content_type,
                "content_text": c.content_text,
                "content_markdown": c.content_markdown,
                "image_caption": c.image_caption,
                "image_path": c.image_path,
                "image_url": f"/api/images/{__import__('os').path.basename(c.image_path)}" if c.image_path else None,
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
                "section_title": c.section_title,
                "document_title": None,
                "filename": None,
                "relevance_score": getattr(c, 'relevance_score', 1.0)
            }
            chunk_dicts.append(chunk_dict)
        
        # Resolve document titles for each chunk
        doc_id_set = list(set(c["document_id"] for c in chunk_dicts))
        if doc_id_set:
            stmt_docs = select(Document.id, Document.title, Document.filename).where(
                Document.id.in_([uuid.UUID(did) for did in doc_id_set])
            )
            res_docs = await db.execute(stmt_docs)
            doc_map = {str(row[0]): (row[1] or row[2]) for row in res_docs.all()}
            for c in chunk_dicts:
                c["document_title"] = doc_map.get(c["document_id"], "Unknown Document")
                c["filename"] = doc_map.get(c["document_id"])
        
        duration_ms = int((time.time() - start_time) * 1000)
        logging.info(f"[RetrievalOrchestrator] Retrieved {len(chunk_dicts)} chunks in {duration_ms}ms (doc_ids={document_ids})")
        
        step = {
            "step_name": "retrieval_orchestrator",
            "input_summary": f"Retrieving chunks for: '{query_text}'",
            "output_summary": f"Retrieved {len(chunk_dicts)} chunks, reranked.",
            "duration_ms": duration_ms,
            "metadata": {
                "chunks_count": len(chunk_dicts),
                "retrieval_types": retrieval_types,
                "document_ids": [str(d) for d in (document_ids or [])]
            }
        }
        
        return {
            "retrieved_chunks": chunk_dicts,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in retrieval_orchestrator_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        step = {
            "step_name": "retrieval_orchestrator",
            "input_summary": f"Retrieving chunks for: '{query_text}'",
            "output_summary": f"Failed: {str(e)}",
            "duration_ms": duration_ms,
            "metadata": {"error": str(e)}
        }
        return {
            "retrieved_chunks": [],
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
