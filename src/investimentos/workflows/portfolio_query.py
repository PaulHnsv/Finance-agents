"""
Portfolio Query workflow — main LangGraph StateGraph.
Routes query through coordinator → specialists → report writer.
"""
from langgraph.graph import StateGraph, END
from investimentos.agents.state import AgentState
from investimentos.agents.coordinator import coordinator_node
from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
from investimentos.agents.portfolio_analyst import portfolio_analyst_node
from investimentos.agents.market_analyst import market_analyst_node
from investimentos.agents.document_ingestor import document_ingestor_node
from investimentos.agents.report_writer import report_writer_node

def route_after_coordinator(state: AgentState) -> str:
    intent = state.intent or "other"
    if intent in ("portfolio_analysis", "report"):
        return "portfolio_data_loader"
    if intent == "market_query":
        return "market_analyst"
    if intent == "document_ingest":
        return "document_ingestor"
    return "report_writer"

def route_after_portfolio(state: AgentState) -> str:
    if state.intent == "report":
        return "market_analyst"
    return "report_writer"

def build_portfolio_query_graph():
    graph = StateGraph(AgentState)

    graph.add_node("coordinator", coordinator_node)
    graph.add_node("portfolio_data_loader", portfolio_data_loader_node)
    graph.add_node("portfolio_analyst", portfolio_analyst_node)
    graph.add_node("market_analyst", market_analyst_node)
    graph.add_node("document_ingestor", document_ingestor_node)
    graph.add_node("report_writer", report_writer_node)

    graph.set_entry_point("coordinator")

    graph.add_conditional_edges(
        "coordinator",
        route_after_coordinator,
        {
            "portfolio_data_loader": "portfolio_data_loader",
            "market_analyst": "market_analyst",
            "document_ingestor": "document_ingestor",
            "report_writer": "report_writer",
        },
    )

    graph.add_edge("portfolio_data_loader", "portfolio_analyst")

    graph.add_conditional_edges(
        "portfolio_analyst",
        route_after_portfolio,
        {
            "market_analyst": "market_analyst",
            "report_writer": "report_writer",
        },
    )

    graph.add_edge("market_analyst", "report_writer")
    graph.add_edge("document_ingestor", END)
    graph.add_edge("report_writer", END)

    return graph.compile()
