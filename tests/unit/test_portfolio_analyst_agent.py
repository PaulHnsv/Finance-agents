from unittest.mock import patch
from investimentos.agents.state import AgentState, DISCLAIMER


@patch("investimentos.agents.portfolio_analyst.chat")
def test_portfolio_analyst_emits_specialist_output(mock_chat, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.portfolio_analyst import portfolio_analyst_node

    mock_chat.return_value = "Análise: carteira concentrada em PETR4."
    state = AgentState(
        user_query="x",
        portfolio_summary={
            "allocation_pct": {"PETR4": 80, "VALE3": 20},
            "hhi": 0.68,
            "max_drawdown_pct": -12.0,
            "twr_pct": 5.2,
            "drift": {"PETR4": 30.0},
        },
    )
    out = portfolio_analyst_node(state)
    assert "specialist_outputs" in out
    assert len(out["specialist_outputs"]) == 1
    assert "Análise" in out["specialist_outputs"][0]
    assert DISCLAIMER in out["specialist_outputs"][0]
    kwargs = mock_chat.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["max_tokens"] == 600
