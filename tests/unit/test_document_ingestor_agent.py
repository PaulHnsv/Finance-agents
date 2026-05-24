from unittest.mock import patch
from investimentos.agents.state import AgentState

_TXN_TEXT = "NOTA DE CORRETAGEM\nCompra de PETR4\nLiquidação D+2"
_SUG_TEXT = "Portfólio Sugerido\nPerfil moderado\nAções Brasil: 40%\nITUB4 5% — banco sólido\nBBDC4 3%"


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value=_TXN_TEXT)
@patch("investimentos.integrations.documents.extrato_parser.chat")
def test_document_ingestor_parses_plain_json(mock_chat, _mock_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.document_ingestor import document_ingestor_node

    mock_chat.return_value = (
        '{"period_end":"2025-01-02","transactions":[{"date":"2025-01-02","ticker":"PETR4",'
        '"type":"compra","quantity":100,"price":30.0,"fees":0.0}],'
        '"equity_snapshot":[{"ticker":"PETR4","quantity":100.0,"avg_cost_hint":30.0}],'
        '"fixed_income_snapshot":[]}'
    )
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(f)))
    assert out["document_type"] == "transactions"
    assert out["extracted_transactions"][0]["ticker"] == "PETR4"
    assert "1 transação" in out["specialist_outputs"][0]


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value=_TXN_TEXT)
@patch("investimentos.integrations.documents.extrato_parser.chat")
def test_document_ingestor_strips_markdown_fences(mock_chat, _mock_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    get_settings.cache_clear()

    from investimentos.agents.document_ingestor import document_ingestor_node

    mock_chat.return_value = (
        '```json\n{"period_end":null,"transactions":[],"equity_snapshot":[],"fixed_income_snapshot":[]}\n```'
    )
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(f)))
    assert out["extracted_transactions"] == []
    assert "0 transação" in out["specialist_outputs"][0]


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value=_TXN_TEXT)
@patch("investimentos.integrations.documents.extrato_parser.chat")
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


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value=_SUG_TEXT)
def test_ingestor_routes_suggested_portfolio(_mock_pdf, tmp_path):
    from investimentos.agents.document_ingestor import document_ingestor_node
    f = tmp_path / "x.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(f)))
    assert out["document_type"] == "suggested_portfolio"
    assert out["extracted_suggestion"]["class_allocations"]
    assert out["extracted_suggestion"]["asset_allocations"][0]["ticker"] == "ITUB4"


@patch("investimentos.agents.document_ingestor.extract_pdf", return_value="texto qualquer sem palavra-chave")
def test_ingestor_unknown_document(_mock_pdf, tmp_path):
    from investimentos.agents.document_ingestor import document_ingestor_node
    f = tmp_path / "x.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = document_ingestor_node(AgentState(user_query="x", document_path=str(f)))
    assert out["document_type"] == "unknown"


def test_agent_state_new_fields():
    s = AgentState(user_query="x", document_type="suggested_portfolio", extracted_suggestion={"k": "v"})
    assert s.document_type == "suggested_portfolio"
    assert s.extracted_suggestion["k"] == "v"
