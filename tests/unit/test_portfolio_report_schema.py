import pytest
from pydantic import ValidationError

from investimentos.agents.schemas.portfolio_report import (
    PortfolioReport, DiversificationFinding, DriftFinding,
    RiskFinding, NextStep,
)
from investimentos.domain.models import AssetClass


def _valid_report(**overrides) -> PortfolioReport:
    defaults = dict(
        summary="Carteira com concentração elevada.",
        diversification=DiversificationFinding(
            hhi=0.62, classification="concentrada", comment="Alta concentração.",
        ),
        drift=[
            DriftFinding(
                asset_class=AssetClass.ACAO, actual_pct=80.0, target_pct=60.0,
                delta_pct=20.0, severity="rebalancear", comment="Acima.",
            ),
        ],
        risks=[
            RiskFinding(ticker="ITUB4", risk_type="concentracao", description="35% em um único papel."),
        ],
        next_steps=[
            NextStep(action="Reduzir ITUB4", priority="alta", rationale="Concentração."),
            NextStep(action="Adicionar RF", priority="media", rationale="Diversificação."),
        ],
    )
    defaults.update(overrides)
    return PortfolioReport(**defaults)


def test_portfolio_report_valid_construction():
    r = _valid_report()
    assert r.diversification.hhi == 0.62
    assert len(r.next_steps) == 2


def test_next_steps_min_length_enforced():
    with pytest.raises(ValidationError):
        _valid_report(next_steps=[NextStep(action="X", priority="alta", rationale="y")])


def test_summary_max_length_enforced():
    with pytest.raises(ValidationError):
        _valid_report(summary="x" * 321)


def test_diversification_classification_literal_enforced():
    with pytest.raises(ValidationError):
        DiversificationFinding(hhi=0.5, classification="meio-termo", comment="x")


def test_risk_type_literal_enforced():
    with pytest.raises(ValidationError):
        RiskFinding(ticker="X", risk_type="random_thing", description="x")
