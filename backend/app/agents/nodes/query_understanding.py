import json
import time
import logging
from langchain_openai import ChatOpenAI

from app.config import settings
from app.agents.state import AgentState
from app.agents.prompts import QUERY_UNDERSTANDING_PROMPT

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
        llm = ChatOpenAI(
            model=settings.openai_model_name,
            openai_api_key=settings.openai_api_key,
            temperature=0.0
        )
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Clean JSON markdown fences if present
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        parsed_json = json.loads(content)
        duration_ms = int((time.time() - start_time) * 1000)
        
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
