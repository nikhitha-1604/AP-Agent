from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from .nodes import (
    extraction_node,
    validation_node,
    matching_node,
    recall_memory_node,
    decision_node,
)


class AgentState(TypedDict, total=False):
    raw_text: str
    extracted_data: Dict
    exceptions: List[Dict]
    recalled_memory: Optional[Dict]
    status: str
    reasoning: List[str]
    invoice_id: int          # DB primary key — set by main.py before invocation


def _route_after_validation(state: AgentState) -> str:
    """
    Conditional edge after validation_node.
    If extraction failed, skip matching and memory recall, go straight to decide.
    Otherwise continue to matching node.
    """
    if state.get("status") == "EXTRACTION_FAILED":
        return "decide"   # decision_node will emit EXCEPTION and terminate
    return "match"


workflow = StateGraph(AgentState)

workflow.add_node("extract", extraction_node)
workflow.add_node("validate", validation_node)
workflow.add_node("match", matching_node)
workflow.add_node("recall_memory", recall_memory_node)
workflow.add_node("decide", decision_node)

workflow.set_entry_point("extract")
workflow.add_edge("extract", "validate")

# Conditional branch: failed extraction bypasses matching
workflow.add_conditional_edges(
    "validate",
    _route_after_validation,
    {
        "match": "match",
        "decide": "decide",
    },
)

workflow.add_edge("match", "recall_memory")
workflow.add_edge("recall_memory", "decide")
workflow.add_edge("decide", END)

app_agent = workflow.compile()

