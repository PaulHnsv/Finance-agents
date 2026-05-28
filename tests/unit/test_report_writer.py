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
