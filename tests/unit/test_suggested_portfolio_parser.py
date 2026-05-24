from decimal import Decimal

from investimentos.integrations.documents.suggested_portfolio_parser import (
    parse_suggested_portfolio,
    parse_suggested_portfolio_with_fallback,
)

SAMPLE = """Portfólio Sugerido
Perfil moderado, horizonte longo prazo.

Alocação por classe:
Ações Brasil: 40%
Renda Fixa: 35%
Internacional: 25%

Ações sugeridas:
ITUB4 5% — Banco com forte super app
BBDC4 3% — Política prudente de risco
PETR4 4% — Diversificação energética
"""


def test_parser_extracts_classes():
    result = parse_suggested_portfolio(SAMPLE)
    classes = {c["asset_class"]: c["target_pct"] for c in result["class_allocations"]}
    assert classes.get("acao") == Decimal("40")
    assert classes.get("renda_fixa") == Decimal("35")


def test_parser_extracts_assets_with_thesis():
    result = parse_suggested_portfolio(SAMPLE)
    assets = {a["ticker"]: a for a in result["asset_allocations"]}
    assert assets["ITUB4"]["target_pct"] == Decimal("5")
    assert "super app" in assets["ITUB4"]["thesis"].lower()


def test_parser_returns_empty_on_no_matches():
    result = parse_suggested_portfolio("nada relevante aqui")
    assert result["class_allocations"] == []
    assert result["asset_allocations"] == []


def test_parser_extracts_header_style_tickers():
    text = """Ações Brasil:

ITUB4 — Itaú Unibanco
Banco com forte super app que aprimora a experiência do cliente.

BBDC4 — Bradesco
Política prudente de risco e governança histórica.
"""
    result = parse_suggested_portfolio(text)
    tickers = {a["ticker"]: a for a in result["asset_allocations"]}
    assert "ITUB4" in tickers
    assert "BBDC4" in tickers
    assert tickers["ITUB4"]["target_pct"] == Decimal("0")
    assert "super app" in tickers["ITUB4"]["thesis"].lower()


def test_parser_falls_back_to_llm(monkeypatch):
    import investimentos.integrations.documents.suggested_portfolio_parser as mod
    monkeypatch.setattr(mod, "_llm_extract", lambda t: {
        "class_allocations": [{"asset_class": "acao", "target_pct": Decimal("100")}],
        "asset_allocations": [],
    })
    result = parse_suggested_portfolio_with_fallback("livre e sem estrutura legível")
    assert result["class_allocations"][0]["asset_class"] == "acao"
