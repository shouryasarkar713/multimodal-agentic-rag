import logging
import uuid
import torch
import open_clip
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sentence_transformers import CrossEncoder

from app.config import settings
from app.models.db import Chunk
from app.services.embedding import get_embeddings_model, get_clip_model

# Lazy-loaded CrossEncoder singleton
_cross_encoder = None

def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        logging.info(f"Loading Cross-Encoder model: {settings.cross_encoder_model_name}")
        _cross_encoder = CrossEncoder(settings.cross_encoder_model_name, device="cpu")
    return _cross_encoder

async def dense_text_search(
    session: AsyncSession,
    query_embedding: List[float],
    document_id: Optional[uuid.UUID] = None,
    limit: int = 50
) -> List[Chunk]:
    """Retrieve text/table chunks using OpenAI vector cosine similarity with Risk 10 fallback."""
    from sqlalchemy import text
    
    # Check total chunks in the database for the search scope
    count_stmt = select(func.count(Chunk.id))
    if document_id:
        count_stmt = count_stmt.where(Chunk.document_id == document_id)
    count_res = await session.execute(count_stmt)
    total_chunks = count_res.scalar() or 0
    
    if total_chunks >= 500:
        # Set probes for IVFFlat index search
        await session.execute(text("SET LOCAL ivfflat.probes = 20"))
        logging.info(f"IVFFlat index active: set ivfflat.probes = 20 (total chunks = {total_chunks})")
    else:
        logging.info(f"Brute-force scan active: bypassing IVFFlat probes (total chunks = {total_chunks} < 500)")
        
    stmt = select(Chunk).where(Chunk.content_type.in_(["text", "table"]))
    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)
        
    stmt = stmt.order_by(Chunk.text_embedding.cosine_distance(query_embedding)).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())

async def sparse_text_search(
    session: AsyncSession,
    query_text: str,
    document_id: Optional[uuid.UUID] = None,
    limit: int = 50
) -> List[Chunk]:
    """Retrieve text/table chunks using PostgreSQL full-text search (tsvector)."""
    # Use plainto_tsquery to safely parse queries without syntax errors
    tsquery = func.plainto_tsquery("english", query_text)
    
    stmt = select(Chunk).where(
        Chunk.content_type.in_(["text", "table"]),
        Chunk.search_vector.op("@@")(tsquery)
    )
    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)
        
    # Rank by cover density
    stmt = stmt.order_by(func.ts_rank_cd(Chunk.search_vector, tsquery).desc()).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())

def reciprocal_rank_fusion(
    dense_results: List[Chunk],
    sparse_results: List[Chunk],
    k: int = 60,
    limit: int = 20
) -> List[Chunk]:
    """Merge and score dense & sparse results using Reciprocal Rank Fusion (RRF)."""
    rrf_scores = {}
    chunk_map = {}
    
    for rank, chunk in enumerate(dense_results):
        chunk_map[chunk.id] = chunk
        # rank is 0-indexed, RRF formula uses 1-indexed rank
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (k + rank + 1))
        
    for rank, chunk in enumerate(sparse_results):
        chunk_map[chunk.id] = chunk
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (k + rank + 1))
        
    # Sort chunks by RRF score descending
    sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
    return [chunk_map[cid] for cid in sorted_ids[:limit]]

async def image_clip_search(
    session: AsyncSession,
    query_text: str,
    document_id: Optional[uuid.UUID] = None,
    limit: int = 10
) -> List[Chunk]:
    """Embed query text using CLIP and retrieve semantically similar figure images."""
    model, _ = get_clip_model()
    
    # Tokenize and encode query text using CLIP
    text_tokens = open_clip.tokenize([query_text])
    with torch.no_grad():
        text_features = model.encode_text(text_tokens)
        # Normalize CLIP query vector
        text_features /= text_features.norm(dim=-1, keepdim=True)
        query_clip_vector = text_features[0].cpu().numpy().tolist()
        
    # Check total chunks for Risk 10
    from sqlalchemy import text
    count_stmt = select(func.count(Chunk.id))
    if document_id:
        count_stmt = count_stmt.where(Chunk.document_id == document_id)
    count_res = await session.execute(count_stmt)
    total_chunks = count_res.scalar() or 0
    
    if total_chunks >= 500:
        await session.execute(text("SET LOCAL ivfflat.probes = 20"))
        logging.info(f"IVFFlat index active for image search: set ivfflat.probes = 20 (total chunks = {total_chunks})")
    else:
        logging.info(f"Brute-force scan active for image search: bypassing IVFFlat probes (total chunks = {total_chunks} < 500)")

    stmt = select(Chunk).where(Chunk.content_type == "image")
    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)
        
    stmt = stmt.order_by(Chunk.image_embedding.cosine_distance(query_clip_vector)).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())

def rerank_candidates(
    query: str,
    candidates: List[Chunk],
    top_k: int = 5
) -> List[Chunk]:
    """Re-rank candidate chunks using Cross-Encoder ms-marco-MiniLM-L-6-v2."""
    if not candidates:
        return []
        
    cross_encoder = get_cross_encoder()
    
    # Format inputs as pairs of (query, chunk_text)
    pairs = []
    for c in candidates:
        text_content = ""
        if c.content_type == "image":
            text_content = c.image_caption or c.content_text or ""
        elif c.content_type == "table":
            text_content = c.content_markdown or c.content_text or ""
        else:
            text_content = c.content_text or ""
        pairs.append((query, text_content))
        
    scores = cross_encoder.predict(pairs)
    
    # Sort candidates based on scores descending
    candidate_scores = list(zip(candidates, scores))
    candidate_scores.sort(key=lambda x: x[1], reverse=True)
    
    return [cs[0] for cs in candidate_scores[:top_k]]

async def retrieve_and_rerank(
    session: AsyncSession,
    query_text: str,
    document_id: Optional[uuid.UUID] = None,
    top_k: int = 5
) -> List[Chunk]:
    """Run full hybrid + multimodal retrieval and cross-encoder re-ranking pipeline."""
    logging.info(f"Retrieving and re-ranking for query: '{query_text}' (doc_id={document_id})")
    
    # 1. Generate query embedding for dense search
    embeddings_model = get_embeddings_model()
    query_embedding = await embeddings_model.aembed_query(query_text)
    
    # 2. Perform parallel hybrid search
    dense_res = await dense_text_search(session, query_embedding, document_id, limit=50)
    sparse_res = await sparse_text_search(session, query_text, document_id, limit=50)
    
    # 3. Perform RRF fusion on text/table candidates
    fused_text_candidates = reciprocal_rank_fusion(dense_res, sparse_res, k=60, limit=20)
    
    # 4. Perform CLIP Multimodal search for image candidates
    image_candidates = await image_clip_search(session, query_text, document_id, limit=10)
    
    # 5. Merge text/table candidates with image candidates
    all_candidates = fused_text_candidates + image_candidates
    
    # 6. Re-rank merged candidates using Cross-Encoder
    ranked_chunks = rerank_candidates(query_text, all_candidates, top_k=top_k)
    
    return ranked_chunks
