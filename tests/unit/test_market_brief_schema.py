import pytest
from pydantic import ValidationError

from investimentos.agents.schemas.market_brief import MarketBrief, TickerMovement


def test_market_brief_minimal_valid():
    mb = MarketBrief(
        summary="Cenário neutro com bovespa estável.",
        ticker_movements=[], macro_notes=[], warnings=[],
    )
    assert mb.summary.startswith("Cenário")


def test_ticker_movement_validates_fields():
    tm = TickerMovement(ticker="ITUB4", change_pct=2.5, comment="Alta moderada.")
    assert tm.change_pct == 2.5


def test_summary_max_length_enforced():
    with pytest.raises(ValidationError):
        MarketBrief(
            summary="x" * 401,
            ticker_movements=[], macro_notes=[], warnings=[],
        )
