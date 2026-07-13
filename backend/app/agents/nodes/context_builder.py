import time
import logging
from app.agents.state import AgentState

async def context_builder_node(state: AgentState) -> dict:
    """Filter, sort, and truncate retrieved chunks to build the prompt context."""
    retrieved_chunks = state.get("retrieved_chunks") or []
    
    start_time = time.time()
    
    # 1. Filter retrieved_chunks to only those with evidence_score >= 3
    filtered_chunks = [c for c in retrieved_chunks if c.get("evidence_score", 1.0) >= 3.0]
    
    # 2. Sort by evidence_score descending
    filtered_chunks.sort(key=lambda x: x.get("evidence_score", 0.0), reverse=True)
    
    # 3. Truncate to fit within 12,000 tokens (estimate: len(text) / 4)
    budget = 12000
    current_tokens = 0
    final_chunks = []
    
    for c in filtered_chunks:
        text_content = c.get("content_text") or c.get("content_markdown") or c.get("image_caption") or ""
        estimated_tokens = len(text_content) // 4
        if current_tokens + estimated_tokens <= budget:
            final_chunks.append(c)
            current_tokens += estimated_tokens
        else:
            # Drop lowest-scored chunks that exceed budget
            break
            
    # 4. Format context as a numbered list with metadata headers
    formatted_parts = []
    for idx, c in enumerate(final_chunks):
        doc_title = c.get("document_title", "Unknown Document")
        page = c.get("page_number", 1)
        sec_title = c.get("section_title") or "General"
        ctype = c.get("content_type", "text")
        
        # For image chunks, include caption and a custom note
        if ctype == "image":
            caption = c.get("image_caption") or "No caption"
            text_body = f"[Figure from page {page}: {caption}]"
        else:
            text_body = c.get("content_markdown") or c.get("content_text") or ""
            
        header = f"[{idx + 1}] Source: \"{doc_title}\", Page {page}, Section: \"{sec_title}\", Type: {ctype}"
        formatted_parts.append(f"{header}\n{text_body}")
        
    formatted_context = "\n\n".join(formatted_parts)
    duration_ms = int((time.time() - start_time) * 1000)
    
    step = {
        "step_name": "context_builder",
        "input_summary": f"Filtering {len(retrieved_chunks)} candidates. Keeps {len(final_chunks)} chunks within token limit.",
        "output_summary": f"Assembled context. Estimated tokens: {current_tokens}.",
        "duration_ms": duration_ms,
        "metadata": {
            "initial_chunks_count": len(retrieved_chunks),
            "final_chunks_count": len(final_chunks),
            "estimated_tokens": current_tokens
        }
    }
    
    # We return the modified retrieved_chunks list AND the formatted context string
    return {
        "retrieved_chunks": final_chunks,
        "formatted_context": formatted_context,
        "trace_steps": (state.get("trace_steps") or []) + [step]
    }
