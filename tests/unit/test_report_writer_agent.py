from unittest.mock import patch
from investimentos.agents.state import AgentState, DISCLAIMER


@patch("investimentos.agents.report_writer.chat")
def test_report_writer_synthesizes(mock_chat, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.report_writer import report_writer_node

    mock_chat.return_value = "# Relatório\nResumo."
    state = AgentState(user_query="x", specialist_outputs=["A", "B"])
    out = report_writer_node(state)
    assert "report_markdown" in out
    assert out["report_markdown"].startswith("# Relatório")
    assert DISCLAIMER in out["report_markdown"]
    kwargs = mock_chat.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["max_tokens"] == 1500


def test_report_writer_no_outputs(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.report_writer import report_writer_node

    out = report_writer_node(AgentState(user_query="x", specialist_outputs=[]))
    assert "Nenhuma análise disponível" in out["report_markdown"]
    assert DISCLAIMER in out["report_markdown"]
