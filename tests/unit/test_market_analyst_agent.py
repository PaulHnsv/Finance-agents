from unittest.mock import patch
from investimentos.agents.state import AgentState, DISCLAIMER


@patch("investimentos.agents.market_analyst.chat")
def test_market_analyst_with_empty_tickers(mock_chat, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.market_analyst import market_analyst_node

    mock_chat.return_value = "Resumo de mercado."
    state = AgentState(user_query="x", portfolio_summary={"allocation_pct": {}})
    out = market_analyst_node(state)
    assert "specialist_outputs" in out
    assert DISCLAIMER in out["specialist_outputs"][0]
    assert out["market_data"] == {}
    kwargs = mock_chat.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["max_tokens"] == 500
