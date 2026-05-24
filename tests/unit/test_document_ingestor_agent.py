from unittest.mock import patch
from investimentos.agents.state import AgentState


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value="texto")
@patch("investimentos.agents.document_ingestor.chat")
def test_document_ingestor_parses_plain_json(mock_chat, _mock_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.document_ingestor import document_ingestor_node

    mock_chat.return_value = (
        '{"document_type": "extrato", '
        '"transactions": [{"date":"2025-01-02","ticker":"PETR4",'
        '"type":"compra","quantity":100,"price":30.0,"fees":0.0}]}'
    )
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(f)))
    assert out["extracted_transactions"][0]["ticker"] == "PETR4"
    assert "1 transação" in out["specialist_outputs"][0]


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value="texto")
@patch("investimentos.agents.document_ingestor.chat")
def test_document_ingestor_strips_markdown_fences(mock_chat, _mock_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.document_ingestor import document_ingestor_node

    mock_chat.return_value = (
        '```json\n{"document_type":"outro","transactions":[]}\n```'
    )
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(f)))
    assert out["extracted_transactions"] == []
    assert "0 transação" in out["specialist_outputs"][0]


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value="texto")
@patch("investimentos.agents.document_ingestor.chat")
def test_document_ingestor_invalid_json_returns_error(mock_chat, _mock_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.document_ingestor import document_ingestor_node

    mock_chat.return_value = "isto não é json"
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(f)))
    assert "error" in out


def test_document_ingestor_missing_path():
    from investimentos.agents.document_ingestor import document_ingestor_node
    out = document_ingestor_node(AgentState(user_query="x", document_path=None))
    assert out == {"error": "Nenhum documento fornecido para ingestão"}


def test_document_ingestor_file_not_found(tmp_path):
    from investimentos.agents.document_ingestor import document_ingestor_node
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(tmp_path / "no.pdf")))
    assert "Arquivo não encontrado" in out["error"]
