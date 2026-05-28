from unittest.mock import patch
from investimentos.agents.state import AgentState
from investimentos.agents.schemas.portfolio_report import (
    PortfolioReport, DiversificationFinding, NextStep, DriftFinding,
)
from investimentos.domain.models import AssetClass


def _fake_report() -> PortfolioReport:
    return PortfolioReport(
        summary="Carteira diversificada.",
        diversification=DiversificationFinding(
            hhi=0.18, classification="diversificada", comment="OK.",
        ),
        drift=[DriftFinding(
            asset_class=AssetClass.ACAO, actual_pct=60.0, target_pct=60.0,
            delta_pct=0.0, severity="ok", comment="Alinhada.",
        )],
        risks=[],
        next_steps=[
            NextStep(action="Manter", priority="baixa", rationale="OK"),
            NextStep(action="Revisar trimestre", priority="baixa", rationale="Higiene"),
        ],
    )


def test_portfolio_analyst_returns_portfolio_report():
    state = AgentState(
        user_query="x",
        portfolio_summary={
            "allocation_pct": {"ITUB4": 60.0, "PETR4": 40.0},
            "hhi": 0.18, "drift": {}, "holdings_detail": [], "source": "transactions",
        },
    )
    with patch(
        "investimentos.agents.portfolio_analyst.chat_structured",
        return_value=_fake_report(),
    ):
        from investimentos.agents.portfolio_analyst import portfolio_analyst_node
        out = portfolio_analyst_node(state)

    assert isinstance(out["portfolio_report"], PortfolioReport)
    assert out["portfolio_report"].diversification.classification == "diversificada"


def test_portfolio_analyst_empty_summary_skips_llm():
    state = AgentState(user_query="x", portfolio_summary={"source": "empty"})
    with patch("investimentos.agents.portfolio_analyst.chat_structured") as mock_chat:
        from investimentos.agents.portfolio_analyst import portfolio_analyst_node
        out = portfolio_analyst_node(state)
    mock_chat.assert_not_called()
    assert out["portfolio_report"] is None
