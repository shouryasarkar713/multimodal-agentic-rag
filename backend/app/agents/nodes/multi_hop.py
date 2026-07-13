import json
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_openai import ChatOpenAI

from app.config import settings
from app.models.db import Document
from app.agents.state import AgentState
from app.agents.prompts import MULTI_HOP_DECOMPOSITION_PROMPT
from app.agents.nodes.retrieval_orchestrator import retrieval_orchestrator_node

async def multi_hop_decomposition_node(state: AgentState, config: dict) -> dict:
    """Decompose comparison queries into simpler sub-queries and retrieve chunks for each."""
    db: AsyncSession = config["configurable"]["db"]
    document_ids: Optional[List[Any]] = config["configurable"].get("document_ids")
    user_query = state.get("user_query", "")
    
    start_time = time.time()
    
    # 1. Fetch available paper titles
    try:
        stmt = select(Document.title, Document.filename)
        if document_ids:
            stmt = stmt.where(Document.id.in_(document_ids))
        res = await db.execute(stmt)
        available_paper_titles = [row[0] or row[1] for row in res.all()]
        available_titles_str = ", ".join(available_paper_titles)
    except Exception as e:
        logging.error(f"Error fetching titles in multi_hop: {e}")
        available_titles_str = ""
        
    prompt = MULTI_HOP_DECOMPOSITION_PROMPT.format(
        user_query=user_query,
        available_paper_titles=available_titles_str
    )
    
    sub_queries = []
    sub_results = []
    
    try:
        llm = ChatOpenAI(
            model=settings.openai_model_name,
            openai_api_key=settings.openai_api_key,
            temperature=0.0
        )
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Clean JSON markdown fences
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        sub_queries = json.loads(content)
        if not isinstance(sub_queries, list):
            raise ValueError("LLM did not return a JSON list of sub-queries.")
            
        # 2. Invoke retrieval_orchestrator for each sub-query
        merged_chunks_map = {}
        for sub_q in sub_queries:
            temp_state = {
                "rewritten_query": sub_q,
                "retrieval_types": state.get("retrieval_types") or ["text"],
                "trace_steps": []
            }
            ret_res = await retrieval_orchestrator_node(temp_state, config)
            chunks = ret_res.get("retrieved_chunks") or []
            
            sub_results.append({
                "sub_query": sub_q,
                "retrieved_chunks": chunks
            })
            
            for chunk in chunks:
                merged_chunks_map[chunk["id"]] = chunk
                
        duration_ms = int((time.time() - start_time) * 1000)
        
        step = {
            "step_name": "multi_hop_decomposition",
            "input_summary": f"Decomposing comparison query: '{user_query}'",
            "output_summary": f"Decomposed into {len(sub_queries)} queries: {sub_queries}. Retrieved {len(merged_chunks_map)} unique chunks.",
            "duration_ms": duration_ms,
            "metadata": {
                "sub_queries": sub_queries,
                "results_counts": [len(res["retrieved_chunks"]) for res in sub_results]
            }
        }
        
        return {
            "sub_queries": sub_queries,
            "sub_results": sub_results,
            "retrieved_chunks": list(merged_chunks_map.values()),
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in multi_hop_decomposition_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Fallback behavior: treat as single paper_qa intent
        step = {
            "step_name": "multi_hop_decomposition",
            "input_summary": f"Decomposing comparison query: '{user_query}'",
            "output_summary": f"Failed (Fallback to paper_qa): {str(e)}",
            "duration_ms": duration_ms,
            "metadata": {"error": str(e)}
        }
        
        # Run retrieval_orchestrator_node directly as fallback
        temp_state = {
            "rewritten_query": user_query,
            "retrieval_types": state.get("retrieval_types") or ["text"],
            "trace_steps": []
        }
        ret_res = await retrieval_orchestrator_node(temp_state, config)
        chunks = ret_res.get("retrieved_chunks") or []
        
        return {
            "sub_queries": [user_query],
            "sub_results": [{"sub_query": user_query, "retrieved_chunks": chunks}],
            "retrieved_chunks": chunks,
            "classified_intent": "paper_qa",  # Change intent to trigger normal flow
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
