"""Market Analyst — produces a typed MarketBrief from current quotes."""
import json

from investimentos.agents.state import AgentState
from investimentos.agents.schemas.market_brief import MarketBrief
from investimentos.config import get_settings
from investimentos.llm.structured import chat_structured

MARKET_PROMPT = """Você é um analista de mercado especializado em B3 e renda fixa brasileira.

Cotações disponíveis (use APENAS os dados presentes; não invente):
{market_data}

Regras:
- summary: 2-3 frases sobre o tom geral do mercado para os ativos listados.
- ticker_movements: um item por ticker presente.
- macro_notes: até 4 notas macro relevantes ao Brasil; vazio se sem dados que sustentem.
- warnings: pontos de atenção. Não emita recomendações de compra/venda.
"""


def _fetch_market_data(tickers: list[str]) -> dict:
    settings = get_settings()
    market_data: dict = {}
    if not tickers:
        return market_data
    try:
        from investimentos.integrations.brapi import BrapiClient
        brapi = BrapiClient(token=settings.brapi_token)
        for q in brapi.get_quotes(tickers):
            if q.get("ticker"):
                market_data[q["ticker"]] = {"price_change_pct": str(q["change_pct"])}
        if market_data:
            return market_data
    except Exception:
        pass
    try:
        from investimentos.integrations.yfinance_adapter import YFinanceClient
        yf = YFinanceClient()
        for ticker in tickers[:10]:
            try:
                q = yf.get_quote(f"{ticker}.SA")
                market_data[ticker] = {"price_change_pct": str(q["change_pct"])}
            except Exception:
                pass
    except Exception:
        pass
    return market_data


def market_analyst_node(state: AgentState) -> dict:
    settings = get_settings()
    summary = state.portfolio_summary or {}
    tickers = list(summary.get("allocation_pct", {}).keys())
    market_data = _fetch_market_data(tickers)

    brief = chat_structured(
        messages=[{
            "role": "user",
            "content": MARKET_PROMPT.format(
                market_data=json.dumps(market_data, ensure_ascii=False),
            ),
        }],
        response_schema=MarketBrief,
        model=settings.llm_model_default,
        max_tokens=700,
    )
    return {"market_brief": brief, "market_data": market_data}
