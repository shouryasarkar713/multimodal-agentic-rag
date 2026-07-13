from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes import (
    query_understanding_node,
    route_by_intent,
    retrieval_orchestrator_node,
    multi_hop_decomposition_node,
    summarization_node,
    evidence_grader_node,
    check_evidence,
    query_rewriter_node,
    context_builder_node,
    generator_node,
    hallucination_validator_node,
    check_validation,
    tool_executor_node,
    finalize_node
)

# Identity node for intent_router routing step
def intent_router_node(state: AgentState) -> dict:
    return {}

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("query_understanding", query_understanding_node)
graph.add_node("intent_router", intent_router_node)
graph.add_node("retrieval_orchestrator", retrieval_orchestrator_node)
graph.add_node("multi_hop_decomposition", multi_hop_decomposition_node)
graph.add_node("summarization", summarization_node)
graph.add_node("tool_executor", tool_executor_node)
graph.add_node("evidence_grader", evidence_grader_node)
graph.add_node("query_rewriter", query_rewriter_node)
graph.add_node("context_builder", context_builder_node)
graph.add_node("generator", generator_node)
graph.add_node("hallucination_validator", hallucination_validator_node)
graph.add_node("finalize", finalize_node)

# Set Entry Point
graph.set_entry_point("query_understanding")

# Standard Edges
graph.add_edge("query_understanding", "intent_router")
graph.add_edge("multi_hop_decomposition", "retrieval_orchestrator")
graph.add_edge("retrieval_orchestrator", "evidence_grader")
graph.add_edge("query_rewriter", "retrieval_orchestrator")
graph.add_edge("context_builder", "generator")
graph.add_edge("generator", "hallucination_validator")
graph.add_edge("summarization", "finalize")
graph.add_edge("tool_executor", "finalize")
graph.add_edge("finalize", END)

# Conditional Edges
graph.add_conditional_edges(
    "intent_router",
    route_by_intent,
    {
        "paper_qa": "retrieval_orchestrator",
        "compare": "multi_hop_decomposition",
        "summarize": "summarization",
        "action": "tool_executor",
    }
)

graph.add_conditional_edges(
    "evidence_grader",
    check_evidence,
    {
        "sufficient": "context_builder",
        "retry": "query_rewriter",
    }
)

graph.add_conditional_edges(
    "hallucination_validator",
    check_validation,
    {
        "pass": "finalize",
        "fail": "generator",
    }
)

compiled_graph = graph.compile()
