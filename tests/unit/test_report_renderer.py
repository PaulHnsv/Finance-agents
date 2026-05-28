from investimentos.agents.schemas.portfolio_report import (
    PortfolioReport, DiversificationFinding, DriftFinding,
    RiskFinding, NextStep,
)
from investimentos.agents.schemas.market_brief import MarketBrief, TickerMovement
from investimentos.agents.rendering.report_renderer import (
    render_portfolio_report, render_market_brief, render_full_report,
)
from investimentos.domain.models import AssetClass


def _report():
    return PortfolioReport(
        summary="Carteira concentrada.",
        diversification=DiversificationFinding(
            hhi=0.62, classification="concentrada", comment="Alta concentração.",
        ),
        drift=[
            DriftFinding(
                asset_class=AssetClass.ACAO, actual_pct=80.0, target_pct=60.0,
                delta_pct=20.0, severity="rebalancear", comment="Acima.",
            ),
            DriftFinding(
                asset_class=AssetClass.RENDA_FIXA, actual_pct=20.0, target_pct=40.0,
                delta_pct=-20.0, severity="atencao", comment="Abaixo.",
            ),
        ],
        risks=[RiskFinding(ticker="ITUB4", risk_type="concentracao", description="35%.")],
        next_steps=[
            NextStep(action="Reduzir ITUB4", priority="alta", rationale="Conc."),
            NextStep(action="Aumentar RF", priority="media", rationale="Div."),
        ],
    )


def test_render_portfolio_report_includes_all_sections():
    md = render_portfolio_report(_report())
    assert "Sumário" in md
    assert "Diversificação" in md
    assert "HHI" in md and "0.62" in md
    assert "concentrada" in md
    assert "Drift" in md
    assert "ITUB4" in md
    assert "Próximos Passos" in md


def test_render_portfolio_report_severity_icons():
    md = render_portfolio_report(_report())
    assert "🔴" in md
    assert "⚠️" in md


def test_render_market_brief():
    brief = MarketBrief(
        summary="Mercado estável.",
        ticker_movements=[TickerMovement(ticker="ITUB4", change_pct=1.5, comment="Alta.")],
        macro_notes=[], warnings=[],
    )
    md = render_market_brief(brief)
    assert "Mercado" in md
    assert "ITUB4" in md
    assert "1.5" in md


def test_render_full_report_combines_both_with_disclaimer():
    md = render_full_report(portfolio_report=_report(), market_brief=None)
    assert "Aviso" in md
    assert "Sumário" in md


def test_render_full_report_handles_none_inputs():
    md = render_full_report(portfolio_report=None, market_brief=None)
    assert "Nenhuma análise disponível" in md
    assert "Aviso" in md
