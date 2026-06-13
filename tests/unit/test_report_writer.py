from investimentos.agents.state import AgentState
from investimentos.agents.report_writer import report_writer_node
from investimentos.agents.schemas.portfolio_report import (
    PortfolioReport, DiversificationFinding, NextStep,
)


def _minimal_report() -> PortfolioReport:
    return PortfolioReport(
        summary="ok",
        diversification=DiversificationFinding(hhi=0.2, classification="moderada", comment="x"),
        drift=[], risks=[],
        next_steps=[
            NextStep(action="a", priority="alta", rationale="b"),
            NextStep(action="c", priority="media", rationale="d"),
        ],
    )


def test_report_writer_renders_from_schema_without_llm():
    state = AgentState(user_query="x", portfolio_report=_minimal_report())
    out = report_writer_node(state)
    assert "Sumário" in out["report_markdown"]
    assert "Aviso" in out["report_markdown"]


def test_report_writer_handles_no_data():
    state = AgentState(user_query="x")
    out = report_writer_node(state)
    assert "Nenhuma análise disponível" in out["report_markdown"]


def test_report_writer_falls_back_to_specialist_outputs():
    state = AgentState(user_query="x", specialist_outputs=["## Custom\n\nFoo bar."])
    out = report_writer_node(state)
    assert "Foo bar" in out["report_markdown"]


def test_report_writer_answers_direct_stock_list_question():
    state = AgentState(
        user_query="quais ações tenho na minha carteira?",
        portfolio_summary={
            "holdings_detail": [
                {
                    "ticker": "WEGE3",
                    "display_name": "WEG",
                    "asset_class": "acao",
                    "allocation_pct": 35.5,
                },
                {
                    "ticker": "KNRI11",
                    "display_name": "Kinea Renda Imobiliária",
                    "asset_class": "fii",
                    "allocation_pct": 12.0,
                },
                {
                    "ticker": "ALUP11",
                    "display_name": "Alupar",
                    "asset_class": "acao",
                    "allocation_pct": 52.5,
                },
            ],
        },
        portfolio_report=_minimal_report(),
    )

    out = report_writer_node(state)

    assert "Ações na carteira" in out["report_markdown"]
    assert "ALUP11" in out["report_markdown"]
    assert "WEGE3" in out["report_markdown"]
    assert "KNRI11" not in out["report_markdown"]
    assert "Relatório da Carteira" not in out["report_markdown"]
