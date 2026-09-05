import json
import re
from typing import Any

def clean_thinking(text: str) -> str:
    """Strip out <think>...</think> reasoning blocks from DeepSeek and similar models."""
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def extract_json(content: str) -> Any:
    """
    Extract and parse JSON from an LLM response string.
    Handles:
    - <think>...</think> reasoning blocks
    - Markdown code fences (```json ... ``` or ``` ... ```)
    - Surrounding conversational text
    - Keys with escaped quotes
    """
    if not content:
        raise ValueError("Empty response content cannot be parsed as JSON")
        
    cleaned = clean_thinking(content)
    
    # 1. Try direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass
        
    # 2. Match ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", cleaned, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass
            
    # 3. Use JSONDecoder.raw_decode on every candidate start bracket (handles trailing text)
    decoder = json.JSONDecoder()
    start_indices = [i for i, c in enumerate(cleaned) if c in '{[']
    for start in start_indices:
        try:
            obj, _ = decoder.raw_decode(cleaned[start:])
            return obj
        except Exception:
            continue

    # 4. Match outermost [ ... ] or { ... }
    bracket_match = re.search(r"([\[{].*[\]}])", cleaned, re.DOTALL)
    if bracket_match:
        try:
            return json.loads(bracket_match.group(1).strip())
        except Exception:
            pass
            
    # 5. Fallback to direct json.loads so exception detail is preserved
    return json.loads(cleaned)
