import json
import time
import logging

from app.agents.llm_factory import get_generation_llm
from app.agents.state import AgentState
from app.agents.prompts import QUERY_UNDERSTANDING_PROMPT
from app.agents.utils import extract_json

async def query_understanding_node(state: AgentState) -> dict:
    """Parse and classify user query."""
    user_query = state.get("user_query", "")
    chat_history = state.get("chat_history") or []
    
    # Format chat history
    chat_history_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history])
    
    # Build prompt
    prompt = QUERY_UNDERSTANDING_PROMPT.format(
        chat_history=chat_history_str,
        user_query=user_query
    )
    
    start_time = time.time()
    
    # Fallback default values
    fallback_result = {
        "classified_intent": "paper_qa",
        "parsed_query": {
            "query_text": user_query,
            "target_papers": [],
            "figure_ref": None,
            "section_ref": None
        },
        "retrieval_types": ["text"],
        "trace_steps": state.get("trace_steps") or []
    }
    
    try:
        logging.info(f"[QueryUnderstanding] Analyzing user query: '{user_query}'")
        llm = get_generation_llm()
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        parsed_json = extract_json(content)
        if not isinstance(parsed_json, dict):
            parsed_json = {}
        duration_ms = int((time.time() - start_time) * 1000)
        logging.info(f"[QueryUnderstanding] Classified intent='{parsed_json.get('intent')}', types={parsed_json.get('retrieval_types')} in {duration_ms}ms")
        
        # Record trace step
        step = {
            "step_name": "query_understanding",
            "input_summary": f"Query: {user_query}",
            "output_summary": f"Intent: {parsed_json.get('intent')}, types: {parsed_json.get('retrieval_types')}",
            "duration_ms": duration_ms,
            "metadata": parsed_json
        }
        
        return {
            "classified_intent": parsed_json.get("intent", "paper_qa"),
            "parsed_query": {
                "query_text": parsed_json.get("query_text", user_query),
                "target_papers": parsed_json.get("target_papers", []),
                "figure_ref": parsed_json.get("figure_ref"),
                "section_ref": parsed_json.get("section_ref")
            },
            "retrieval_types": parsed_json.get("retrieval_types", ["text"]),
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in query_understanding_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        fallback_result["trace_steps"] = (state.get("trace_steps") or []) + [{
            "step_name": "query_understanding",
            "input_summary": f"Query: {user_query}",
            "output_summary": f"Failed (Fallback to paper_qa): {str(e)}",
            "duration_ms": duration_ms,
            "metadata": {"error": str(e)}
        }]
        return fallback_result
