import json
import time
import logging
from langchain_openai import ChatOpenAI

from app.config import settings
from app.agents.state import AgentState
from app.agents.prompts import HALLUCINATION_VALIDATION_PROMPT

async def hallucination_validator_node(state: AgentState) -> dict:
    """Validate that every cited claim in the generated answer exists in the retrieved context."""
    answer = state.get("generated_answer", "")
    formatted_context = state.get("formatted_context", "")
    prev_validation = state.get("validation_passed")
    
    start_time = time.time()
    
    # If no answer or context, pass by default
    if not answer or not formatted_context.strip():
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "validation_passed": True,
            "validation_issues": [],
            "trace_steps": (state.get("trace_steps") or []) + [{
                "step_name": "hallucination_validator",
                "input_summary": "Skipped validation (empty answer or context)",
                "output_summary": "Passed",
                "duration_ms": duration_ms,
                "metadata": {}
            }]
        }
        
    prompt = HALLUCINATION_VALIDATION_PROMPT.format(
        generated_answer=answer,
        formatted_context=formatted_context
    )
    
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
        
        parsed_json = json.loads(content)
        overall_supported = parsed_json.get("overall_supported", True)
        
        claims = parsed_json.get("claims") or []
        validation_issues = [c.get("issue") for c in claims if not c.get("supported") and c.get("issue")]
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 1. Determine validation status and apply retries / disclaimers
        if overall_supported:
            val_passed = True
            output_answer = answer
        else:
            # Failed validation
            if prev_validation is None:
                # First attempt: fail validation, route back to generator
                val_passed = False
                output_answer = answer
            else:
                # Already failed once (second attempt): force pass and add disclaimer
                val_passed = True
                disclaimer = (
                    "\n\n> Some claims in this answer could ⚠️ "
                    "not be fully verified against the source material. Please "
                    "check the cited sources directly."
                )
                output_answer = answer + disclaimer
                
        step = {
            "step_name": "hallucination_validator",
            "input_summary": f"Validating answer claims against context",
            "output_summary": f"Claims verified. overall_supported: {overall_supported}, validation_passed: {val_passed}. Issues count: {len(validation_issues)}",
            "duration_ms": duration_ms,
            "metadata": parsed_json
        }
        
        return {
            "validation_passed": val_passed,
            "validation_issues": validation_issues,
            "generated_answer": output_answer,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    except Exception as e:
        logging.error(f"Error in hallucination_validator_node: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Fallback default: pass validation to avoid graph deadlocks, log error
        return {
            "validation_passed": True,
            "validation_issues": [f"Validation failed with exception: {str(e)}"],
            "trace_steps": (state.get("trace_steps") or []) + [{
                "step_name": "hallucination_validator",
                "input_summary": "Validating answer claims against context",
                "output_summary": f"Failed (Fallback to pass): {str(e)}",
                "duration_ms": duration_ms,
                "metadata": {"error": str(e)}
            }]
        }

def check_validation(state: AgentState) -> str:
    """Conditional edge routing for hallucination check."""
    if state.get("validation_passed"):
        return "pass"
    return "fail"
