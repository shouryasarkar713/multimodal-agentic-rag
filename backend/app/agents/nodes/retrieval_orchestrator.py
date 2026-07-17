import os
import uuid
import logging
import time
import torch
import open_clip
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.config import settings
from app.models.db import Chunk, Document
from app.agents.state import AgentState
from app.services.embedding import get_embeddings_model, get_clip_model
from app.services.retrieval import get_cross_encoder, reciprocal_rank_fusion

async def retrieval_orchestrator_node(state: AgentState, config: dict) -> dict:
    """Orchestrates dense, sparse, CLIP image, and metadata searches."""
    db: AsyncSession = config["configurable"]["db"]
    document_ids: Optional[List[uuid.UUID]] = config["configurable"].get("document_ids")
    
    # 1. Determine query text
    query_text = state.get("rewritten_query") or state.get("parsed_query", {}).get("query_text") or state.get("user_query")
    retrieval_types = state.get("retrieval_types") or ["text"]
    
    start_time = time.time()
    retrieved_chunks_map = {}
    chunk_counts_by_type = {}
    
    # Check for direct figure/chunk override (Bug 1)
    direct_chunk_id = None
    if query_text and "EXPLAIN_FIGURE:" in query_text:
        try:
            parts = query_text.split("EXPLAIN_FIGURE:")
            if len(parts) > 1:
                potential_id = parts[1].split("]")[0].strip()
                direct_chunk_id = uuid.UUID(potential_id)
        except Exception as e:
            logging.error(f"Failed to parse direct chunk ID: {e}")
            
    try:
        # Fetch direct chunk if requested
        if direct_chunk_id:
            try:
                stmt_direct = select(Chunk).where(Chunk.id == direct_chunk_id)
                res_direct = await db.execute(stmt_direct)
                direct_chunk = res_direct.scalar_one_or_none()
                if direct_chunk:
                    retrieved_chunks_map[direct_chunk.id] = direct_chunk
                    chunk_counts_by_type["image"] = 1
                    logging.info(f"Directly retrieved requested figure chunk: {direct_chunk_id}")
            except Exception as e:
                logging.error(f"Error retrieving direct chunk: {e}")

        # Load embeddings model
        embeddings_model = get_embeddings_model()
        query_embedding = await embeddings_model.aembed_query(query_text)
        
        # Plain tsquery for safe PostgreSQL FTS
        tsquery = func.plainto_tsquery("english", query_text)
        
        # Execute retrievals based on retrieval_types
        for rtype in retrieval_types:
            if rtype == "text":
                # Dense
                stmt_dense = select(Chunk).where(Chunk.content_type.in_(["text", "table"]))
                if document_ids:
                    stmt_dense = stmt_dense.where(Chunk.document_id.in_(document_ids))
                stmt_dense = stmt_dense.order_by(Chunk.text_embedding.cosine_distance(query_embedding)).limit(20)
                res_dense = await db.execute(stmt_dense)
                dense_results = res_dense.scalars().all()
                
                # Sparse
                stmt_sparse = select(Chunk).where(
                    Chunk.content_type.in_(["text", "table"]),
                    Chunk.search_vector.op("@@")(tsquery)
                )
                if document_ids:
                    stmt_sparse = stmt_sparse.where(Chunk.document_id.in_(document_ids))
                stmt_sparse = stmt_sparse.order_by(func.ts_rank_cd(Chunk.search_vector, tsquery).desc()).limit(20)
                res_sparse = await db.execute(stmt_sparse)
                sparse_results = res_sparse.scalars().all()
                
                # Merge RRF
                merged = reciprocal_rank_fusion(dense_results, sparse_results, k=60, limit=20)
                for c in merged:
                    retrieved_chunks_map[c.id] = c
                chunk_counts_by_type["text"] = len(merged)
                
            elif rtype == "table":
                # Dense
                stmt_dense = select(Chunk).where(Chunk.content_type == "table")
                if document_ids:
                    stmt_dense = stmt_dense.where(Chunk.document_id.in_(document_ids))
                stmt_dense = stmt_dense.order_by(Chunk.text_embedding.cosine_distance(query_embedding)).limit(10)
                res_dense = await db.execute(stmt_dense)
                dense_results = res_dense.scalars().all()
                
                # Sparse
                stmt_sparse = select(Chunk).where(
                    Chunk.content_type == "table",
                    Chunk.search_vector.op("@@")(tsquery)
                )
                if document_ids:
                    stmt_sparse = stmt_sparse.where(Chunk.document_id.in_(document_ids))
                stmt_sparse = stmt_sparse.order_by(func.ts_rank_cd(Chunk.search_vector, tsquery).desc()).limit(10)
                res_sparse = await db.execute(stmt_sparse)
                sparse_results = res_sparse.scalars().all()
                
                merged = reciprocal_rank_fusion(dense_results, sparse_results, k=60, limit=10)
                for c in merged:
                    retrieved_chunks_map[c.id] = c
                chunk_counts_by_type["table"] = len(merged)
                
            elif rtype == "image":
                if direct_chunk_id and direct_chunk_id in retrieved_chunks_map:
                    # Already fetched requested figure chunk directly, bypass search to prevent semantic drift (Bug 1)
                    pass
                else:
                    # Two-pronged search: (a) CLIP query-image cosine similarity
                    model, _ = get_clip_model()
                    text_tokens = open_clip.tokenize([query_text])
                    with torch.no_grad():
                        text_features = model.encode_text(text_tokens)
                        text_features /= text_features.norm(dim=-1, keepdim=True)
                        query_clip_vector = text_features[0].cpu().numpy().tolist()
                    
                    stmt_clip = select(Chunk).where(Chunk.content_type == "image")
                    if document_ids:
                        stmt_clip = stmt_clip.where(Chunk.document_id.in_(document_ids))
                    stmt_clip = stmt_clip.order_by(Chunk.image_embedding.cosine_distance(query_clip_vector)).limit(10)
                    res_clip = await db.execute(stmt_clip)
                    clip_results = res_clip.scalars().all()
                    
                    # (b) Caption dense text search
                    stmt_caption = select(Chunk).where(Chunk.content_type == "image")
                    if document_ids:
                        stmt_caption = stmt_caption.where(Chunk.document_id.in_(document_ids))
                    stmt_caption = stmt_caption.order_by(Chunk.text_embedding.cosine_distance(query_embedding)).limit(10)
                    res_caption = await db.execute(stmt_caption)
                    caption_results = res_caption.scalars().all()
                    
                    merged = reciprocal_rank_fusion(clip_results, caption_results, k=60, limit=10)
                    for c in merged:
                        retrieved_chunks_map[c.id] = c
                    chunk_counts_by_type["image"] = len(merged)
                
            elif rtype == "metadata":
                # Documents metadata search
                stmt_doc = select(Document)
                if document_ids:
                    stmt_doc = stmt_doc.where(Document.id.in_(document_ids))
                stmt_doc = stmt_doc.where(
                    or_(
                        Document.title.ilike(f"%{query_text}%"),
                        Document.authors.any(query_text)
                    )
                ).limit(5)
                res_doc = await db.execute(stmt_doc)
                docs = res_doc.scalars().all()
                
                # Build pseudo-chunks
                count = 0
                for d in docs:
                    pseudo_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"metadata-{d.id}")
                    # Construct a Chunk-like structure
                    pseudo_chunk = Chunk(
                        id=pseudo_id,
                        document_id=d.id,
                        content_type="text",
                        content_text=f"Document Title: {d.title}\nAuthors: {', '.join(d.authors or [])}\nAbstract: {d.abstract or ''}",
                        page_number=1,
                        section_title="Metadata"
                    )
                    retrieved_chunks_map[pseudo_id] = pseudo_chunk
                    count += 1
                chunk_counts_by_type["metadata"] = count
                
        # 4. Rerank using Cross-Encoder (only text and table chunks)
        text_and_table_chunks = [c for c in retrieved_chunks_map.values() if c.content_type in ["text", "table"]]
        ce_reranked = []
        if text_and_table_chunks:
            cross_encoder = get_cross_encoder()
            pairs = [[query_text, c.content_text] for c in text_and_table_chunks]
            scores = cross_encoder.predict(pairs)
            for chunk, score in zip(text_and_table_chunks, scores):
                ce_reranked.append((chunk, float(score)))
            ce_reranked.sort(key=lambda x: x[1], reverse=True)
            ce_reranked = [item[0] for item in ce_reranked[:10]] # Top 10 after reranking
            
        # Compile final retrieved chunks list (retaining images/metadata, updating text/tables)
        final_retrieved = []
        # Add reranked text/table chunks
        final_retrieved.extend(ce_reranked)
        # Add image chunks
        final_retrieved.extend([c for c in retrieved_chunks_map.values() if c.content_type == "image"])
        # Add metadata pseudo-chunks
        final_retrieved.extend([c for c in retrieved_chunks_map.values() if c.id not in [x.id for x in final_retrieved]])
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record trace step
        step = {
            "step_name": "retrieval_orchestrator",
            "input_summary": f"Retrieving for query: '{query_text}' with types {retrieval_types}",
            "output_summary": f"Retrieved {len(final_retrieved)} chunks total (counts: {chunk_counts_by_type})",
            "duration_ms": duration_ms,
            "metadata": {
                "chunk_counts": chunk_counts_by_type,
                "retrieved_ids": [str(c.id) for c in final_retrieved]
            }
        }
        
        return {
            "retrieved_chunks": final_retrieved,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in retrieval_orchestrator_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "retrieved_chunks": list(retrieved_chunks_map.values()),
            "trace_steps": (state.get("trace_steps") or []) + [{
                "step_name": "retrieval_orchestrator",
                "input_summary": f"Retrieving for query: '{query_text}' with types {retrieval_types}",
                "output_summary": f"Failed: {str(e)}",
                "duration_ms": duration_ms,
                "metadata": {"error": str(e)}
            }]
        }
