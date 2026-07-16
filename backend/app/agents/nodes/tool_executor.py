import os
import re
import io
import time
import base64
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from PIL import Image

from app.agents.llm_factory import get_generation_llm
from app.config import settings
from app.models.db import Chunk, Document
from app.agents.state import AgentState
from app.agents.prompts import EXPLAIN_FIGURE_PROMPT, SUMMARIZATION_PROMPT
from langchain_core.messages import HumanMessage

def get_image_base64(image_path: str) -> str:
    """Load image from disk, resize to max 512px on longest edge, and base64 encode."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found on disk: {image_path}")
        
    with Image.open(image_path) as img:
        img.thumbnail((512, 512))
        buffered = io.BytesIO()
        # Save as PNG
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

async def explain_figure_action(state: AgentState, db: AsyncSession, document_ids: Optional[List[Any]]) -> dict:
    """Implement 'Explain this figure' action with fuzzy matching and GPT-4.1 vision."""
    parsed_query = state.get("parsed_query") or {}
    figure_ref = parsed_query.get("figure_ref") or "Figure"
    
    # 1. Fuzzy matching strategy for figure (Risk 3 mitigation)
    # Extract number from figure_ref (e.g. "Figure 3" -> "3")
    num_match = re.search(r'\d+', figure_ref)
    num = num_match.group(0) if num_match else None
    
    # Query all image chunks for the document(s)
    stmt = select(Chunk).where(Chunk.content_type == "image")
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))
    stmt = stmt.order_by(Chunk.chunk_index.asc())
    res = await db.execute(stmt)
    img_chunks = res.scalars().all()
    
    target_chunk = None
    
    if img_chunks:
        if num:
            # Step 1.1: Try exact match on image_caption containing the number
            for c in img_chunks:
                caption = c.image_caption or ""
                if f" {num}" in caption or f"fig {num}" in caption.lower() or f"figure {num}" in caption.lower():
                    target_chunk = c
                    break
                    
            # Step 1.2: Try regex match: r'[Ff]ig(?:ure)?\.?\s*num'
            if not target_chunk:
                pattern = re.compile(rf'[Ff]ig(?:ure)?\.?\s*{num}')
                for c in img_chunks:
                    caption = c.image_caption or ""
                    if pattern.search(caption):
                        target_chunk = c
                        break
                        
            # Step 1.3: Fall back to N-th image chunk (1-indexed) by index
            if not target_chunk:
                idx = int(num) - 1
                if 0 <= idx < len(img_chunks):
                    target_chunk = img_chunks[idx]
        else:
            # Default to first image chunk
            target_chunk = img_chunks[0]
            
    # 1.4: If still no match, return available figures list
    if not target_chunk:
        captions_list = [f"- Page {c.page_number}: {c.image_caption or 'No caption'}" for c in img_chunks]
        captions_str = "\n".join(captions_list) if captions_list else "No figures extracted."
        answer = f"I couldn't identify '{figure_ref}' in this document. Here are the available figures:\n{captions_str}"
        return {
            "generated_answer": answer,
            "citations": [],
            "figure_refs": [],
            "confidence_score": 0.5
        }
        
    # 2. Load and encode image
    # Resolve absolute image path
    rel_path = target_chunk.image_path or ""
    # Normalize paths: if absolute, keep as is; if relative, prepend data directory
    abs_image_path = rel_path if os.path.isabs(rel_path) else os.path.join(settings.data_dir, "images", os.path.basename(rel_path))
    
    try:
        base64_image = get_image_base64(abs_image_path)
    except Exception as e:
        logging.error(f"Failed to load image in tool_executor: {e}")
        return {
            "generated_answer": f"Failed to load the figure image from path {abs_image_path}: {str(e)}",
            "citations": [],
            "figure_refs": [],
            "confidence_score": 0.0
        }
        
    # 3. Retrieve 3 closest text chunks by page number
    stmt_closest = (
        select(Chunk)
        .where(
            Chunk.document_id == target_chunk.document_id,
            Chunk.content_type.in_(["text", "table"])
        )
        .order_by(
            func.abs(Chunk.page_number - target_chunk.page_number).asc(),
            Chunk.chunk_index.asc()
        )
        .limit(3)
    )
    res_closest = await db.execute(stmt_closest)
    closest_chunks = res_closest.scalars().all()
    
    surrounding_text = "\n\n".join(
        [f"Page {c.page_number} ({c.section_title or 'General'}):\n{c.content_text or ''}" for c in closest_chunks]
    )
    
    # Fetch document details
    doc = await db.get(Document, target_chunk.document_id)
    doc_title = doc.title if doc else "Document"
    
    prompt = EXPLAIN_FIGURE_PROMPT.format(
        document_title=doc_title,
        page_number=target_chunk.page_number,
        caption=target_chunk.image_caption or "No caption",
        surrounding_text=surrounding_text
    )
    
    # 4. Invoke LLM with multimodal message
    llm = get_generation_llm()

    content = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}"
            }
        }
    ]
    
    msg = HumanMessage(content=content)
    response = await llm.ainvoke([msg])
    answer = response.content.strip()
    
    # Build citation and figure ref
    citations = []
    for c in closest_chunks:
        citations.append({
            "chunk_id": str(c.id),
            "document_id": str(c.document_id),
            "document_title": doc_title,
            "page_number": c.page_number,
            "section_title": c.section_title or "General",
            "excerpt": (c.content_text or "")[:200],
            "relevance_score": 5.0
        })
        
    figure_refs = [{
        "chunk_id": str(target_chunk.id),
        "document_id": str(target_chunk.document_id),
        "image_path": f"/api/images/{os.path.basename(target_chunk.image_path)}",
        "caption": target_chunk.image_caption or "Figure caption",
        "page_number": target_chunk.page_number
    }]
    
    return {
        "generated_answer": answer,
        "citations": citations,
        "figure_refs": figure_refs,
        "confidence_score": 0.95
    }

async def summarize_section_action(state: AgentState, db: AsyncSession, document_ids: Optional[List[Any]]) -> dict:
    """Implement 'Summarize this section' action."""
    parsed_query = state.get("parsed_query") or {}
    section_ref = parsed_query.get("section_ref") or "Section"
    
    # Retrieve chunks matching section_ref
    stmt = select(Chunk).where(Chunk.section_title.ilike(f"%{section_ref}%"))
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))
    res = await db.execute(stmt)
    chunks = res.scalars().all()
    
    if not chunks:
        return {
            "generated_answer": f"I couldn't find any section matching '{section_ref}' in this document.",
            "citations": [],
            "figure_refs": [],
            "confidence_score": 0.5
        }
        
    # Format chunks
    context_parts = []
    for i, c in enumerate(chunks):
        context_parts.append(f"[{i+1}] Page {c.page_number} ({c.section_title}): {c.content_text or ''}")
    context_str = "\n\n".join(context_parts)
    
    prompt = SUMMARIZATION_PROMPT.format(
        context=context_str,
        target_description=f"Section: {section_ref}"
    )
    
    # Resolve titles
    all_doc_ids = list(set([c.document_id for c in chunks]))
    doc_titles = {}
    if all_doc_ids:
        stmt_titles = select(Document.id, Document.title, Document.filename).where(Document.id.in_(all_doc_ids))
        res_titles = await db.execute(stmt_titles)
        for d_id, d_title, d_fname in res_titles.all():
            doc_titles[d_id] = d_title or d_fname
            
    llm = get_generation_llm()
    response = await llm.ainvoke(prompt)
    answer = response.content.strip()
    
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
        
    return {
        "generated_answer": answer,
        "citations": citations,
        "figure_refs": [],
        "confidence_score": 0.9
    }

async def tool_executor_node(state: AgentState, config: dict) -> dict:
    """Router and executor node for figure explanations and section summarizations."""
    db: AsyncSession = config["configurable"]["db"]
    document_ids: Optional[List[Any]] = config["configurable"].get("document_ids")
    parsed_query = state.get("parsed_query") or {}
    
    start_time = time.time()
    
    try:
        if parsed_query.get("figure_ref"):
            # Run explain figure action
            action_res = await explain_figure_action(state, db, document_ids)
            action_name = "explain_figure"
        elif parsed_query.get("section_ref"):
            # Run summarize section action
            action_res = await summarize_section_action(state, db, document_ids)
            action_name = "summarize_section"
        else:
            # Default fallback: summarize section or explain first figure
            action_res = await explain_figure_action(state, db, document_ids)
            action_name = "explain_figure_fallback"
            
        duration_ms = int((time.time() - start_time) * 1000)
        
        step = {
            "step_name": "tool_executor",
            "input_summary": f"Executing tool action '{action_name}'",
            "output_summary": f"Completed execution. Citations: {len(action_res['citations'])}, Figures: {len(action_res['figure_refs'])}",
            "duration_ms": duration_ms,
            "metadata": {"action": action_name}
        }
        
        return {
            "generated_answer": action_res["generated_answer"],
            "citations": action_res["citations"],
            "figure_refs": action_res["figure_refs"],
            "confidence_score": action_res["confidence_score"],
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in tool_executor_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "generated_answer": f"Tool execution failed: {str(e)}",
            "citations": [],
            "figure_refs": [],
            "confidence_score": 0.0,
            "trace_steps": (state.get("trace_steps") or []) + [{
                "step_name": "tool_executor",
                "input_summary": f"Executing tool action",
                "output_summary": f"Failed: {str(e)}",
                "duration_ms": duration_ms,
                "metadata": {"error": str(e)}
            }]
        }
