from app.agents.state import AgentState

def route_by_intent(state: AgentState) -> str:
    """Return the classified intent or default to paper_qa to route to the correct sub-graph path."""
    return state.get("classified_intent") or "paper_qa"
