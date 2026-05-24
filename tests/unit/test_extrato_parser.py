import pytest
from unittest.mock import patch
from investimentos.integrations.documents.extrato_parser import parse_extrato

_FULL_RESPONSE = (
    '{"period_end":"2026-05-22",'
    '"transactions":[{"date":"2026-05-22","ticker":"ITUB4","type":"compra","quantity":12.0,"price":39.38,"fees":0.02}],'
    '"equity_snapshot":[{"ticker":"ITUB4","quantity":12.0,"avg_cost_hint":39.38}],'
    '"fixed_income_snapshot":[{"name":"CDB Banco Fibra","issuer":"Banco Fibra","maturity_date":null,'
    '"invested_amount":5000.0,"rate_description":"113% CDI","current_value":5100.0}]}'
)


def _mock_chat(messages, model, max_tokens):
    return _FULL_RESPONSE


@patch("investimentos.integrations.documents.extrato_parser.chat", side_effect=_mock_chat)
def test_parse_extrato_period_end(mock_chat):
    result = parse_extrato("extrato text")
    assert result["period_end"] == "2026-05-22"


@patch("investimentos.integrations.documents.extrato_parser.chat", side_effect=_mock_chat)
def test_parse_extrato_transactions(mock_chat):
    result = parse_extrato("extrato text")
    assert len(result["transactions"]) == 1
    assert result["transactions"][0]["ticker"] == "ITUB4"
    assert result["transactions"][0]["type"] == "compra"


@patch("investimentos.integrations.documents.extrato_parser.chat", side_effect=_mock_chat)
def test_parse_extrato_equity_snapshot(mock_chat):
    result = parse_extrato("extrato text")
    assert len(result["equity_snapshot"]) == 1
    assert result["equity_snapshot"][0]["ticker"] == "ITUB4"
    assert result["equity_snapshot"][0]["quantity"] == 12.0


@patch("investimentos.integrations.documents.extrato_parser.chat", side_effect=_mock_chat)
def test_parse_extrato_fixed_income_snapshot(mock_chat):
    result = parse_extrato("extrato text")
    assert len(result["fixed_income_snapshot"]) == 1
    fi = result["fixed_income_snapshot"][0]
    assert fi["name"] == "CDB Banco Fibra"
    assert fi["rate_description"] == "113% CDI"


@patch(
    "investimentos.integrations.documents.extrato_parser.chat",
    return_value=f"```json\n{_FULL_RESPONSE}\n```",
)
def test_parse_extrato_strips_markdown_fences(mock_chat):
    result = parse_extrato("text")
    assert result["period_end"] == "2026-05-22"


def test_parse_extrato_bad_json_returns_none():
    with patch("investimentos.integrations.documents.extrato_parser.chat", return_value="not json"):
        result = parse_extrato("text")
    assert result is None
