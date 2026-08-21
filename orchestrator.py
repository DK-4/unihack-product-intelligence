"""
Pipeline orchestration using LangGraph.

Discovery -> Standardization -> Enrichment -> Trust
                                                 |
                                                 v
                                          Human Review (conditional)

LangGraph operates over a plain dict state (its convention), so we
convert ProductState <-> dict at the graph boundary and run each
agent's `run(ProductState) -> ProductState` function as a node.
"""

from __future__ import annotations

from typing import TypedDict

from agents import discovery_agent, enrichment_agent, standardization_agent, trust_agent
from models.state import ProductState


class GraphState(TypedDict):
    product_state: dict


def _wrap(agent_module):
    def node(graph_state: GraphState) -> GraphState:
        state = ProductState.model_validate(graph_state["product_state"])
        state = agent_module.run(state)
        return {"product_state": state.model_dump(mode="json")}

    return node


def build_graph():
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as e:
        raise ImportError(
            "langgraph is not installed. Run: pip install langgraph"
        ) from e

    graph = StateGraph(GraphState)
    graph.add_node("discovery", _wrap(discovery_agent))
    graph.add_node("standardization", _wrap(standardization_agent))
    graph.add_node("enrichment", _wrap(enrichment_agent))
    graph.add_node("trust", _wrap(trust_agent))

    graph.set_entry_point("discovery")
    graph.add_edge("discovery", "standardization")
    graph.add_edge("standardization", "enrichment")
    graph.add_edge("enrichment", "trust")
    graph.add_edge("trust", END)

    return graph.compile()


def run_pipeline(state: ProductState) -> ProductState:
    """Runs the full 4-agent pipeline and returns the final ProductState.

    Falls back to plain sequential execution if LangGraph isn't
    installed, so the pipeline still works without that dependency.
    """
    try:
        app = build_graph()
        result = app.invoke({"product_state": state.model_dump(mode="json")})
        return ProductState.model_validate(result["product_state"])
    except ImportError:
        state = discovery_agent.run(state)
        state = standardization_agent.run(state)
        state = enrichment_agent.run(state)
        state = trust_agent.run(state)
        return state
