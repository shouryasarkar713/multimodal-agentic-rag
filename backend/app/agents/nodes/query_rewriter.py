import time
import logging

from app.agents.llm_factory import get_generation_llm
from app.agents.state import AgentState
from app.agents.prompts import QUERY_REWRITE_PROMPT

async def query_rewriter_node(state: AgentState) -> dict:
    """Rewrite query to improve search results when the previous attempt retrieved low-relevance evidence."""
    parsed_query = state.get("parsed_query") or {}
    original_query = parsed_query.get("query_text") or state.get("user_query")
    retrieved_chunks = state.get("retrieved_chunks") or []
    attempt = state.get("retrieval_attempt", 0)
    
    start_time = time.time()
    
    # Format a summary of the low-scoring chunks
    low_scoring_list = []
    for idx, c in enumerate(retrieved_chunks[:10]):
        score = c.get("evidence_score", 1.0)
        content_snippet = (c.get("content_text") or c.get("content_markdown") or c.get("image_caption") or "")[:100]
        low_scoring_list.append(
            f"- Chunk {idx} (Paper: '{c.get('document_title')}', Score: {score}): {content_snippet}..."
        )
    low_scoring_chunks_summary = "\n".join(low_scoring_list) if low_scoring_list else "No chunks retrieved."
    
    prompt = QUERY_REWRITE_PROMPT.format(
        original_query=original_query,
        low_scoring_chunks_summary=low_scoring_chunks_summary
    )
    
    try:
        llm = get_generation_llm()
        response = await llm.ainvoke(prompt)
        rewritten = response.content.strip()
        
        # Clean quotes if LLM wrapped it in quotes
        if (rewritten.startswith('"') and rewritten.endswith('"')) or (rewritten.startswith("'") and rewritten.endswith("'")):
            rewritten = rewritten[1:-1].strip()
            
        duration_ms = int((time.time() - start_time) * 1000)
        
        step = {
            "step_name": "query_rewriter",
            "input_summary": f"Rewriting query: '{original_query}'",
            "output_summary": f"Rewritten to: '{rewritten}'",
            "duration_ms": duration_ms,
            "metadata": {"original_query": original_query, "rewritten_query": rewritten, "attempt": attempt + 1}
        }
        
        return {
            "rewritten_query": rewritten,
            "retrieval_attempt": attempt + 1,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in query_rewriter_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Safe default: reuse original query, still increment attempt to prevent infinite loop
        step = {
            "step_name": "query_rewriter",
            "input_summary": f"Rewriting query: '{original_query}'",
            "output_summary": f"Failed (Fallback to original): {str(e)}",
            "duration_ms": duration_ms,
            "metadata": {"error": str(e)}
        }
        
        return {
            "rewritten_query": original_query,
            "retrieval_attempt": attempt + 1,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
