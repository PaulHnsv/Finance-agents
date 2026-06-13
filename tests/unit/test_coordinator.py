from unittest.mock import patch
from investimentos.agents.state import AgentState


@patch("investimentos.agents.coordinator.chat")
def test_coordinator_returns_valid_intent(mock_chat, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.coordinator import coordinator_node

    mock_chat.return_value = "Portfolio_Analysis"
    out = coordinator_node(AgentState(user_query="como está minha carteira?"))
    assert out == {"intent": "portfolio_analysis"}
    assert mock_chat.call_count == 1
    kwargs = mock_chat.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-4o-mini"
    assert kwargs["max_tokens"] == 20


@patch("investimentos.agents.coordinator.chat")
def test_coordinator_falls_back_to_other(mock_chat, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.coordinator import coordinator_node

    mock_chat.return_value = "categoria_inexistente"
    out = coordinator_node(AgentState(user_query="oi"))
    assert out == {"intent": "other"}


@patch("investimentos.agents.coordinator.chat")
def test_coordinator_routes_direct_holdings_question_without_llm(mock_chat, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.coordinator import coordinator_node

    out = coordinator_node(AgentState(user_query="quais ações tenho na minha carteira?"))
    assert out == {"intent": "portfolio_analysis"}
    mock_chat.assert_not_called()
