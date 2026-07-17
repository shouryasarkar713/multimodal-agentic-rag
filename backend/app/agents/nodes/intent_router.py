from app.agents.state import AgentState

def route_by_intent(state: AgentState) -> str:
    """Return the classified intent or default to paper_qa to route to the correct sub-graph path."""
    intent = state.get("classified_intent") or "paper_qa"
    parsed_query = state.get("parsed_query") or {}
    
    # Guardrail: If classified as action but has no specific target reference, route as standard paper_qa
    if intent == "action":
        if not parsed_query.get("figure_ref") and not parsed_query.get("section_ref"):
            return "paper_qa"
            
    return intent
