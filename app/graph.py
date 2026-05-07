from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from app.models import (
    ParsedRequirements, Architecture,
    CostLineItem, SecurityItem
)


class GraphState(TypedDict):
    description: str
    constraints: Optional[str]
    session_id: str
    start_time: float
    requirements: Optional[ParsedRequirements]
    architecture: Optional[Architecture]
    mermaid_diagram: Optional[str]
    cost_estimate: Optional[list[CostLineItem]]
    security_recommendations: Optional[list[SecurityItem]]
    terraform_code: Optional[str]
    current_agent: str
    error: Optional[str]


def create_graph():
    """Create and compile the LangGraph workflow"""
    try:
        from app.agents.requirements import run_requirements_agent
        from app.agents.architecture import run_architecture_agent
        from app.agents.diagram import run_diagram_agent
        from app.agents.cost import run_cost_agent
        from app.agents.security import run_security_agent
        from app.agents.terraform import run_terraform_agent
    except ImportError as e:
        raise RuntimeError(f"Failed to import agents: {e}")

    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("requirements", run_requirements_agent)
    graph.add_node("architecture", run_architecture_agent)
    graph.add_node("diagram", run_diagram_agent)
    graph.add_node("cost", run_cost_agent)
    graph.add_node("security", run_security_agent)
    graph.add_node("terraform", run_terraform_agent)

    # Set entry point
    graph.set_entry_point("requirements")

    # Add edges for sequential workflow
    graph.add_edge("requirements", "architecture")
    graph.add_edge("architecture", "diagram")
    graph.add_edge("diagram", "cost")
    graph.add_edge("cost", "security")
    graph.add_edge("security", "terraform")
    graph.add_edge("terraform", END)

    return graph.compile()