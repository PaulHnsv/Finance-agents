"""Market Analyst — fetches quotes for portfolio holdings and provides context."""
import json

from investimentos.agents.state import AgentState, DISCLAIMER
from investimentos.config import get_settings
from investimentos.llm.client import chat

MARKET_PROMPT = """Você é um analista de mercado especializado em B3 e renda fixa brasileira.

Com base nas cotações e dados de mercado abaixo, forneça um resumo do cenário atual para os ativos da carteira:

{market_data}

Foque em:
- Movimentos relevantes de preço
- Contexto macro brasileiro relevante
- Pontos de atenção para os ativos listados

Máx. 250 palavras. Não emita recomendações de compra/venda."""


def market_analyst_node(state: AgentState) -> dict:
    settings = get_settings()
    summary = state.portfolio_summary or {}
    tickers = list(summary.get("allocation_pct", {}).keys())

    market_data: dict = {}
    if tickers:
        try:
            from investimentos.integrations.brapi import BrapiClient
            brapi = BrapiClient(token=settings.brapi_token)
            quotes = brapi.get_quotes(tickers)
            market_data = {
                q["ticker"]: {"price_change_pct": str(q["change_pct"])}
                for q in quotes if q.get("ticker")
            }
        except Exception:
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

    analysis = chat(
        messages=[{
            "role": "user",
            "content": MARKET_PROMPT.format(
                market_data=json.dumps(market_data, ensure_ascii=False),
            ),
        }],
        model=settings.llm_model_default,
        max_tokens=500,
    )
    output = f"## 📈 Análise de Mercado\n\n{analysis}{DISCLAIMER}"
    return {"specialist_outputs": [output], "market_data": market_data}
