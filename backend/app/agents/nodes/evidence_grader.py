import json
import time
import logging
from typing import List, Dict, Any

from app.agents.llm_factory import get_generation_llm
from app.agents.state import AgentState
from app.agents.prompts import EVIDENCE_GRADING_PROMPT

async def evidence_grader_node(state: AgentState) -> dict:
    """Grade the retrieved chunks to determine if they contain sufficient evidence to answer the query."""
    retrieved_chunks = state.get("retrieved_chunks") or []
    query_text = state.get("rewritten_query") or state.get("parsed_query", {}).get("query_text") or state.get("user_query")
    attempt = state.get("retrieval_attempt", 0)
    
    start_time = time.time()
    
    # Check for direct figure/chunk override (Bug 1)
    direct_chunk_id = None
    user_query = state.get("user_query") or ""
    if "EXPLAIN_FIGURE:" in user_query:
        try:
            parts = user_query.split("EXPLAIN_FIGURE:")
            if len(parts) > 1:
                potential_id = parts[1].split("]")[0].strip()
                import uuid
                direct_chunk_id = uuid.UUID(potential_id)
        except Exception:
            pass

    if direct_chunk_id:
        updated_chunks = []
        evidence_scores = []
        for c in retrieved_chunks:
            chunk_copy = dict(c)
            c_id = chunk_copy.get("id")
            if c_id and (str(c_id) == str(direct_chunk_id)):
                score = 5.0
            else:
                score = 3.0
            chunk_copy["evidence_score"] = score
            updated_chunks.append(chunk_copy)
            evidence_scores.append(score)
            
        duration_ms = int((time.time() - start_time) * 1000)
        step = {
            "step_name": "evidence_grader",
            "input_summary": f"Direct figure explanation bypass for chunk {direct_chunk_id}",
            "output_summary": f"Bypassed LLM grading. sufficient: True",
            "duration_ms": duration_ms,
            "metadata": {"bypass": True, "direct_chunk_id": str(direct_chunk_id)}
        }
        return {
            "evidence_scores": evidence_scores,
            "evidence_sufficient": True,
            "retrieved_chunks": updated_chunks,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    # 1. Take top 10 chunks to grade
    chunks_to_grade = retrieved_chunks[:10]
    
    # If no chunks at all, immediately fail sufficiency and decide route
    if not chunks_to_grade:
        duration_ms = int((time.time() - start_time) * 1000)
        is_sufficient = False
        
        # If we reached max retries, force sufficiency to proceed with best effort
        if attempt >= 2:
            is_sufficient = True
            
        step = {
            "step_name": "evidence_grader",
            "input_summary": f"Grading retrieved chunks for: '{query_text}'",
            "output_summary": f"No chunks retrieved. sufficient: {is_sufficient}",
            "duration_ms": duration_ms,
            "metadata": {"scores": [], "sufficient": is_sufficient, "attempt": attempt}
        }
        
        return {
            "evidence_scores": [],
            "evidence_sufficient": is_sufficient,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    # Format chunks for prompt
    formatted_list = []
    for idx, c in enumerate(chunks_to_grade):
        content = c.get("content_text") or c.get("content_markdown") or c.get("image_caption") or ""
        formatted_list.append(
            f"Chunk {idx} (Paper: \"{c.get('document_title', 'Unknown')}\", Page {c.get('page_number', 1)}, Type: {c.get('content_type', 'text')}):\n{content}\n---"
        )
    chunks_formatted = "\n".join(formatted_list)
    
    prompt = EVIDENCE_GRADING_PROMPT.format(
        query=query_text,
        chunks_formatted=chunks_formatted
    )
    
    try:
        llm = get_generation_llm()
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Clean JSON markdown fences
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        parsed_scores = json.loads(content)
        
        # Build score lookup map
        scores_map = {item["chunk_index"]: float(item["score"]) for item in parsed_scores}
        
        # Assign scores to chunks_to_grade in order
        evidence_scores = []
        for idx in range(len(chunks_to_grade)):
            score = scores_map.get(idx, 3.0) # Default to 3 (somewhat relevant) if missing
            evidence_scores.append(score)
            
        # Update retrieved_chunks list with graded scores
        updated_chunks = []
        for idx, c in enumerate(retrieved_chunks):
            chunk_copy = dict(c)
            if idx < len(evidence_scores):
                chunk_copy["evidence_score"] = evidence_scores[idx]
            else:
                chunk_copy["evidence_score"] = 1.0 # Default low score for ungraded
            updated_chunks.append(chunk_copy)
            
        # 2. Sufficiency check:
        # - At least 3 chunks scored >= 4
        high_score_count = sum(1 for s in evidence_scores if s >= 4.0)
        
        # - Mean score of top 5 chunks >= 3.5
        top_5_scores = sorted(evidence_scores, reverse=True)[:5]
        mean_score = sum(top_5_scores) / len(top_5_scores) if top_5_scores else 0.0
        
        is_sufficient = (high_score_count >= 3) and (mean_score >= 3.5)
        
        # 3. Handle attempt capping
        if not is_sufficient and attempt >= 2:
            logging.info(f"Evidence insufficient but max attempt ({attempt}) reached. Forcing sufficiency.")
            is_sufficient = True
            
        duration_ms = int((time.time() - start_time) * 1000)
        
        step = {
            "step_name": "evidence_grader",
            "input_summary": f"Grading {len(chunks_to_grade)} retrieved chunks",
            "output_summary": f"Graded chunks. High score count: {high_score_count}, mean top 5: {mean_score:.2f}. sufficient: {is_sufficient}",
            "duration_ms": duration_ms,
            "metadata": {
                "scores": evidence_scores,
                "high_score_count": high_score_count,
                "mean_top_5": mean_score,
                "sufficient": is_sufficient,
                "attempt": attempt
            }
        }
        
        return {
            "evidence_scores": evidence_scores,
            "evidence_sufficient": is_sufficient,
            "retrieved_chunks": updated_chunks,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in evidence_grader_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Safe default: mark as sufficient to prevent infinite loops, log error
        fallback_scores = [3.0] * len(chunks_to_grade)
        
        step = {
            "step_name": "evidence_grader",
            "input_summary": f"Grading retrieved chunks",
            "output_summary": f"Failed (Fallback to sufficient): {str(e)}",
            "duration_ms": duration_ms,
            "metadata": {"error": str(e)}
        }
        
        return {
            "evidence_scores": fallback_scores,
            "evidence_sufficient": True,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }

def check_evidence(state: AgentState) -> str:
    """Conditional edge routing based on evidence sufficiency."""
    if state.get("evidence_sufficient"):
        return "sufficient"
    return "retry"
