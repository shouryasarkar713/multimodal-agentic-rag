import json
import time
import logging

from app.agents.llm_factory import get_generation_llm
from app.agents.state import AgentState
from app.agents.prompts import HALLUCINATION_VALIDATION_PROMPT
from app.agents.utils import extract_json

async def hallucination_validator_node(state: AgentState) -> dict:
    """Validate that the generated answer does not contain hallucinated claims."""
    answer = state.get("generated_answer", "")
    formatted_context = state.get("formatted_context", "")
    prev_validation = state.get("validation_passed")
    
    start_time = time.time()
    
    # Fast-path: if answer is empty or default safety response, skip validation
    if not answer or "I couldn't find relevant information" in answer:
        duration_ms = int((time.time() - start_time) * 1000)
        step = {
            "step_name": "hallucination_validator",
            "input_summary": "Skipping validation for fallback answer",
            "output_summary": "Skipped. validation_passed: True",
            "duration_ms": duration_ms,
            "metadata": {"skipped": True}
        }
        return {
            "validation_passed": True,
            "validation_issues": [],
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }
        
    prompt = HALLUCINATION_VALIDATION_PROMPT.format(
        context=formatted_context,
        answer=answer
    )
    
    try:
        llm = get_generation_llm()
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        parsed_json = extract_json(content)
        if not isinstance(parsed_json, dict):
            parsed_json = {}
            
        overall_supported = parsed_json.get("overall_supported", True)
        claims = parsed_json.get("claims") or []
        validation_issues = [c.get("issue") for c in claims if not c.get("supported") and c.get("issue")]
        
        duration_ms = int((time.time() - start_time) * 1000)
        logging.info(f"[Validator] overall_supported={overall_supported}, val_passed={overall_supported} in {duration_ms}ms")
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
        
        # Fallback: pass validation so we don't break answer output
        step = {
            "step_name": "hallucination_validator",
            "input_summary": "Validating answer claims against context",
            "output_summary": f"Validation failed with exception ({str(e)}). Passed through gracefully.",
            "duration_ms": duration_ms,
            "metadata": {"error": str(e), "fallback": True}
        }
        return {
            "validation_passed": True,
            "validation_issues": [],
            "generated_answer": answer,
            "trace_steps": (state.get("trace_steps") or []) + [step]
        }

def check_validation(state: AgentState) -> str:
    """Conditional edge router based on validation_passed."""
    passed = state.get("validation_passed")
    if passed is False:
        return "fail"
    return "pass"
