from typing import TypedDict, Literal, Annotated
import uuid

class AgentState(TypedDict):
    # Input
    user_query: str
    session_id: str
    chat_history: list[dict] # [{"role": "user"|"assistant", "content": "..."}]
    
    # Query understanding
    classified_intent: Literal["paper_qa", "compare", "summarize", "action"] | None
    parsed_query: dict | None # {"query_text": str, "target_papers": list[str], "figure_ref": str|None, "section_ref": str|None}
    retrieval_types: list[str] # Subset of ["text", "table", "image", "metadata"]
    
    # Retrieval
    retrieved_chunks: list[dict] # List of chunk dicts with scores
    formatted_context: str # Formatted numbered context list
    retrieval_attempt: int # 0, 1, or 2 (max retries)
    rewritten_query: str | None # Query after rewrite
    
    # Multi-hop
    sub_queries: list[str] # Decomposed sub-queries for comparison
    sub_results: list[dict] # Results per sub-query
    
    # Evidence grading
    evidence_scores: list[float] # Relevance scores per chunk (1-5)
    evidence_sufficient: bool # True if enough high-quality evidence
    
    # Generation
    generated_answer: str
    citations: list[dict]
    figure_refs: list[dict]
    confidence_score: float
    
    # Validation
    validation_passed: bool
    validation_issues: list[str]
    
    # Trace
    trace_steps: list[dict]
    trace_id: str
