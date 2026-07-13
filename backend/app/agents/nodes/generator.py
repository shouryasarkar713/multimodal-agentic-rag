import re
import os
import time
import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI

from app.config import settings
from app.agents.state import AgentState
from app.agents.prompts import GENERATION_PROMPT

async def generator_node(state: AgentState) -> dict:
    """Generate final answer using retrieved context and query history."""
    retrieved_chunks = state.get("retrieved_chunks") or []
    formatted_context = state.get("formatted_context", "")
    user_query = state.get("user_query", "")
    chat_history = state.get("chat_history") or []
    attempt = state.get("retrieval_attempt", 0)
    validation_passed = state.get("validation_passed")
    
    start_time = time.time()
    
    # Empty retrieval results safety guardrail
    if not retrieved_chunks or not formatted_context.strip():
        duration_ms = int((time.time() - start_time) * 1000)
        answer = "I couldn't find relevant information in the uploaded papers for this question. Try rephrasing or uploading additional papers."
        
        step = {
            "step_name": "generator",
            "input_summary": f"Generating answer for: '{user_query}'",
            "output_summary": "No retrieved context. Returned safety fallback answer.",
            "duration_ms": duration_ms,
            "metadata": {"fallback_triggered": True}
        }
        
        return {
            "generated_answer": answer,
            "citations": [],
            "figure_refs": [],
            "confidence_score": 0.0,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    # Format chat history
    chat_history_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history])
    
    # 1. Build prompt
    prompt = GENERATION_PROMPT.format(
        formatted_context=formatted_context,
        chat_history=chat_history_str,
        user_query=user_query
    )
    
    # 2. Append stricter instructions if re-generating after validation failure
    if validation_passed is False:
        prompt += (
            "\n\nIMPORTANT: Your previous answer contained claims not supported by the provided sources. "
            "This time, ONLY make claims that are directly stated in the numbered sources above. If you are unsure, say so."
        )
        
    try:
        llm = ChatOpenAI(
            model=settings.openai_model_name,
            openai_api_key=settings.openai_api_key,
            temperature=0.0
        )
        response = await llm.ainvoke(prompt)
        answer = response.content.strip()
        
        # 3. Parse inline citations [N]
        citations = []
        seen_citations = set()
        
        # Regex to find [N]
        inline_cits = re.findall(r'\[(\d+)\]', answer)
        for num_str in inline_cits:
            idx = int(num_str) - 1
            if 0 <= idx < len(retrieved_chunks):
                chunk = retrieved_chunks[idx]
                chunk_id = chunk["id"]
                if chunk_id not in seen_citations:
                    seen_citations.add(chunk_id)
                    citations.append({
                        "chunk_id": chunk_id,
                        "document_id": chunk["document_id"],
                        "document_title": chunk.get("document_title"),
                        "page_number": chunk["page_number"],
                        "section_title": chunk.get("section_title"),
                        "excerpt": (chunk.get("content_text") or chunk.get("image_caption") or "")[:200],
                        "relevance_score": chunk.get("relevance_score", 5.0)
                    })
                    
        # 4. Parse figure references [Figure from source N]
        figure_refs = []
        seen_figures = set()
        
        figure_matches = re.findall(r'\[Figure from source (\d+)\]', answer)
        for num_str in figure_matches:
            idx = int(num_str) - 1
            if 0 <= idx < len(retrieved_chunks):
                chunk = retrieved_chunks[idx]
                if chunk.get("content_type") == "image":
                    chunk_id = chunk["id"]
                    if chunk_id not in seen_figures:
                        seen_figures.add(chunk_id)
                        
                        image_path = chunk.get("image_url")
                        if not image_path and chunk.get("image_path"):
                            image_path = f"/api/images/{os.path.basename(chunk['image_path'])}"
                            
                        figure_refs.append({
                            "chunk_id": chunk_id,
                            "document_id": chunk["document_id"],
                            "image_path": image_path,
                            "caption": chunk.get("image_caption") or chunk.get("section_title") or "Figure reference",
                            "page_number": chunk["page_number"]
                        })
                        
        # Check if any standard cited chunk is an image and add it to figure_refs if missed
        for c in citations:
            matched_chunk = next((chunk for chunk in retrieved_chunks if chunk["id"] == c["chunk_id"]), None)
            if matched_chunk and matched_chunk.get("content_type") == "image":
                chunk_id = matched_chunk["id"]
                if chunk_id not in seen_figures:
                    seen_figures.add(chunk_id)
                    image_path = matched_chunk.get("image_url")
                    if not image_path and matched_chunk.get("image_path"):
                        image_path = f"/api/images/{os.path.basename(matched_chunk['image_path'])}"
                        
                    figure_refs.append({
                        "chunk_id": chunk_id,
                        "document_id": matched_chunk["document_id"],
                        "image_path": image_path,
                        "caption": matched_chunk.get("image_caption") or matched_chunk.get("section_title") or "Figure reference",
                        "page_number": matched_chunk["page_number"]
                    })
                    
        # 5. Post-process to remove invalid citations (Risk 4 mitigation)
        # Any [N] where N > len(retrieved_chunks) is replaced with "[citation not found]"
        def replace_invalid_citations(match):
            num = int(match.group(1))
            if num <= 0 or num > len(retrieved_chunks):
                return "[citation not found]"
            return match.group(0)
            
        answer = re.sub(r'\[(\d+)\]', replace_invalid_citations, answer)
        
        # 6. Calculate confidence_score
        confidence = 1.0
        
        # Subtract 0.15 if query was rewritten
        if attempt > 0:
            confidence -= 0.15
            
        # Subtract 0.2 if re-generated after validation failure
        if validation_passed is False:
            confidence -= 0.2
            
        # Subtract 0.1 if mean evidence score < 4.0
        evidence_scores = [c.get("evidence_score", 1.0) for c in retrieved_chunks]
        mean_evidence = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0
        if mean_evidence < 4.0:
            confidence -= 0.1
            
        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        step = {
            "step_name": "generator",
            "input_summary": f"Generating answer for: '{user_query}'",
            "output_summary": f"Generated answer of length {len(answer)} chars. Citations: {len(citations)}, Figures: {len(figure_refs)}. Confidence: {confidence:.2f}",
            "duration_ms": duration_ms,
            "metadata": {
                "citations_count": len(citations),
                "figures_count": len(figure_refs),
                "confidence_score": confidence,
                "mean_evidence": mean_evidence
            }
        }
        
        return {
            "generated_answer": answer,
            "citations": citations,
            "figure_refs": figure_refs,
            "confidence_score": confidence,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in generator_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "generated_answer": f"Failed to generate answer: {str(e)}",
            "citations": [],
            "figure_refs": [],
            "confidence_score": 0.0,
            "trace_steps": (state.get("trace_steps") or []) + [{
                "step_name": "generator",
                "input_summary": f"Generating answer for: '{user_query}'",
                "output_summary": f"Failed: {str(e)}",
                "duration_ms": duration_ms,
                "metadata": {"error": str(e)}
            }]
        }
