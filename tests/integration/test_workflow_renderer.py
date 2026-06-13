"""Integration test — workflow routes through schema-based renderer end-to-end."""
from unittest.mock import patch

from investimentos.agents.schemas.portfolio_report import (
    PortfolioReport, DiversificationFinding, NextStep,
)


def _fake_report() -> PortfolioReport:
    return PortfolioReport(
        summary="ok",
        diversification=DiversificationFinding(hhi=0.2, classification="moderada", comment="x"),
        drift=[], risks=[],
        next_steps=[
            NextStep(action="a", priority="alta", rationale="b"),
            NextStep(action="c", priority="media", rationale="d"),
        ],
    )


def test_workflow_routes_through_renderer_for_portfolio_analysis(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.workflows.portfolio_query import build_portfolio_query_graph

    with patch(
        "investimentos.agents.coordinator.chat",
        return_value="portfolio_analysis",
    ), patch(
        "investimentos.agents.portfolio_data_loader.portfolio_data_loader_node",
        return_value={"portfolio_summary": {
            "allocation_pct": {"ITUB4": 100.0},
            "hhi": 1.0, "source": "transactions",
            "holdings_detail": [], "drift": {},
        }},
    ), patch(
        "investimentos.agents.portfolio_analyst.chat_structured",
        return_value=_fake_report(),
    ):
        graph = build_portfolio_query_graph()
        result = graph.invoke({"user_query": "analisar carteira"})

    assert "Sumário" in result["report_markdown"]
    assert "Aviso" in result["report_markdown"]


def test_workflow_answers_direct_stock_list_without_portfolio_analysis(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.workflows.portfolio_query import build_portfolio_query_graph

    with patch(
        "investimentos.agents.coordinator.chat",
        return_value="portfolio_analysis",
    ), patch(
        "investimentos.workflows.portfolio_query.portfolio_data_loader_node",
        return_value={"portfolio_summary": {
            "source": "transactions",
            "allocation_pct": {"WEGE3": 40.0, "KNRI11": 60.0},
            "hhi": 0.52,
            "holdings_detail": [
                {
                    "ticker": "WEGE3",
                    "display_name": "WEG",
                    "asset_class": "acao",
                    "allocation_pct": 40.0,
                },
                {
                    "ticker": "KNRI11",
                    "display_name": "Kinea Renda Imobiliária",
                    "asset_class": "fii",
                    "allocation_pct": 60.0,
                },
            ],
        }},
    ), patch(
        "investimentos.agents.portfolio_analyst.chat_structured",
        side_effect=AssertionError("portfolio analyst should not run for direct holdings list"),
    ):
        graph = build_portfolio_query_graph()
        result = graph.invoke({"user_query": "quais ações tenho na minha carteira?"})

    assert "Ações na carteira" in result["report_markdown"]
    assert "WEGE3" in result["report_markdown"]
    assert "KNRI11" not in result["report_markdown"]
    assert "Relatório da Carteira" not in result["report_markdown"]
