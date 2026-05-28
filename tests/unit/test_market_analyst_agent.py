from unittest.mock import patch
from investimentos.agents.state import AgentState
from investimentos.agents.schemas.market_brief import MarketBrief, TickerMovement


def test_market_analyst_returns_market_brief():
    fake = MarketBrief(
        summary="Mercado estável.",
        ticker_movements=[TickerMovement(ticker="ITUB4", change_pct=1.0, comment="Alta.")],
        macro_notes=[], warnings=[],
    )
    state = AgentState(
        user_query="x",
        portfolio_summary={"allocation_pct": {"ITUB4": 100.0}},
    )

    with patch(
        "investimentos.agents.market_analyst.chat_structured",
        return_value=fake,
    ), patch(
        "investimentos.agents.market_analyst._fetch_market_data",
        return_value={"ITUB4": {"price_change_pct": "1.0"}},
    ):
        from investimentos.agents.market_analyst import market_analyst_node
        out = market_analyst_node(state)

    assert isinstance(out["market_brief"], MarketBrief)
    assert out["market_brief"].summary == "Mercado estável."
