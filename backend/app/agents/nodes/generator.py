import re
import os
import time
import logging
from typing import List, Dict, Any

from app.agents.llm_factory import get_generation_llm
from app.agents.state import AgentState
from app.agents.prompts import GENERATION_PROMPT
from app.agents.utils import clean_thinking

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
    
    # 1. Build prompt safely avoiding KeyError from any LaTeX curly braces
    prompt = (
        GENERATION_PROMPT
        .replace("{formatted_context}", formatted_context)
        .replace("{chat_history}", chat_history_str)
        .replace("{user_query}", user_query)
    )

    
    # 2. Append stricter instructions if re-generating after validation failure
    if validation_passed is False:
        prompt += (
            "\n\nIMPORTANT: Your previous answer contained claims not supported by the provided sources. "
            "This time, ONLY make claims that are directly stated in the numbered sources above. If you are unsure, say so."
        )
        
    try:
        llm = get_generation_llm()
        response = await llm.ainvoke(prompt)
        answer = clean_thinking(response.content.strip())
        
        # 3. Parse all inline references: standard [N] and figure citations [Figure from source N]
        citations = []
        seen_chunk_ids = set()
        old_to_new_num = {}

        # Collect all referenced source numbers in order of appearance
        ref_matches = re.finditer(r'\[(?:Figure(?:\s*\d+)?\s*from\s*(?:source\s*)?)?(\d+)\]', answer, re.IGNORECASE)
        for m in ref_matches:
            num_str = m.group(1)
            idx = int(num_str) - 1
            if 0 <= idx < len(retrieved_chunks):
                chunk = retrieved_chunks[idx]
                chunk_id = chunk["id"]
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    new_idx = len(citations) + 1
                    old_to_new_num[num_str] = str(new_idx)
                    
                    # Extract image_url if this is an image chunk or has image_path
                    image_url = chunk.get("image_url")
                    if not image_url and chunk.get("image_path"):
                        image_url = f"/api/images/{os.path.basename(chunk['image_path'])}"
                        
                    citations.append({
                        "chunk_id": chunk_id,
                        "document_id": chunk["document_id"],
                        "document_title": chunk.get("document_title"),
                        "filename": chunk.get("filename"),
                        "page_number": chunk["page_number"],
                        "section_title": chunk.get("section_title"),
                        "excerpt": (chunk.get("content_text") or chunk.get("image_caption") or "")[:200],
                        "relevance_score": chunk.get("relevance_score", 5.0),
                        "image_url": image_url
                    })
                elif num_str not in old_to_new_num:
                    existing_new_idx = next((i + 1 for i, c in enumerate(citations) if c["chunk_id"] == chunk_id), 1)
                    old_to_new_num[num_str] = str(existing_new_idx)

        # 4. Attach page figures to citations if on a page with an image
        figure_refs = []
        seen_figures = set()

        for c in citations:
            matched_chunk = next((chunk for chunk in retrieved_chunks if chunk["id"] == c["chunk_id"]), None)
            if matched_chunk:
                img_url = matched_chunk.get("image_url")
                if not img_url and matched_chunk.get("image_path"):
                    img_url = f"/api/images/{os.path.basename(matched_chunk['image_path'])}"
                
                # Check for page image if not directly attached
                if not img_url:
                    page_num = matched_chunk.get("page_number")
                    page_img = next(
                        (ch for ch in retrieved_chunks if (ch.get("content_type") == "image" or ch.get("image_path")) and ch.get("page_number") == page_num),
                        None
                    )
                    if page_img:
                        img_url = page_img.get("image_url") or (f"/api/images/{os.path.basename(page_img['image_path'])}" if page_img.get("image_path") else None)

                if img_url:
                    c["image_url"] = img_url
                    if c["chunk_id"] not in seen_figures:
                        seen_figures.add(c["chunk_id"])
                        figure_refs.append({
                            "chunk_id": c["chunk_id"],
                            "document_id": c["document_id"],
                            "image_path": img_url,
                            "caption": c.get("section_title") or f"Figure from page {c.get('page_number', 1)}",
                            "page_number": c.get("page_number", 1)
                        })

        # Also capture any explicit [Figure ... from source N] that points to an image
        figure_matches = re.finditer(r'\[Figure(?:\\s*(\d+))?\\s*from\\s*(?:source\\s*)?(\\d+)\]', answer, re.IGNORECASE)
        for m in figure_matches:
            fig_label_num = m.group(1)
            num_str = m.group(2)
            idx = int(num_str) - 1
            if 0 <= idx < len(retrieved_chunks):
                chunk = retrieved_chunks[idx]
                chunk_id = chunk["id"]
                if chunk_id not in seen_figures:
                    seen_figures.add(chunk_id)
                    img_path = chunk.get("image_url")
                    if not img_path and chunk.get("image_path"):
                        img_path = f"/api/images/{os.path.basename(chunk['image_path'])}"
                    if img_path:
                        cap = chunk.get("image_caption") or chunk.get("section_title") or f"Figure {fig_label_num or ''} from page {chunk.get('page_number')}"
                        figure_refs.append({
                            "chunk_id": chunk_id,
                            "document_id": chunk["document_id"],
                            "image_path": img_path,
                            "caption": cap.strip(),
                            "page_number": chunk.get("page_number", 1)
                        })

        # 5. Renumber citations in answer text:
        # First renumber [Figure ... from source N]
        def replace_fig_citations(match):
            prefix = match.group(1) or ""
            old_num = match.group(2)
            new_num = old_to_new_num.get(old_num, old_num)
            if prefix.strip():
                return f"[Figure {prefix.strip()} from source {new_num}]"
            return f"[Figure from source {new_num}]"

        answer = re.sub(r'\[Figure(?:\s*(\d+))?\s*from\s*(?:source\s*)?(\d+)\]', replace_fig_citations, answer, flags=re.IGNORECASE)

        # Next renumber standard inline citations [N]
        def replace_inline_citations(match):
            old_num = match.group(1)
            if old_num in old_to_new_num:
                return f"[{old_to_new_num[old_num]}]"
            num = int(old_num)
            if num <= 0 or num > len(retrieved_chunks):
                return "[citation not found]"
            return match.group(0)

        answer = re.sub(r'(?<!Figure\s)(?<!from source )\[(\d+)\]', replace_inline_citations, answer, flags=re.IGNORECASE)

        
        # 6. Calculate confidence_score
        confidence = 1.0
        
        # Subtract 0.1 if query was rewritten (once)
        if attempt > 0:
            confidence -= 0.1
            
        # Subtract 0.15 if this is a re-generation after validation failure on prior attempt
        # Only penalize when validation_passed is explicitly False AND we are in a retry pass
        # (validation_passed=False means the PREVIOUS validator run failed, so this is the retry)
        if validation_passed is False:
            confidence -= 0.15
            
        # Subtract 0.1 if mean evidence score < 3.5 (truly low quality evidence)
        evidence_scores = [c.get("evidence_score", 1.0) for c in retrieved_chunks]
        mean_evidence = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0
        if mean_evidence < 3.5:
            confidence -= 0.1
            
        # Clamp: minimum 0.65 for any answer that completed the full pipeline, max 1.0
        confidence = max(0.65, min(1.0, confidence))

        
        duration_ms = int((time.time() - start_time) * 1000)
        logging.info(f"[Generator] Generated answer in {duration_ms}ms ({len(answer)} chars, {len(citations)} citations, {len(figure_refs)} figures)")
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
