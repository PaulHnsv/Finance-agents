"""Portfolio Analyst — produces a typed PortfolioReport via structured LLM output."""
import json

from investimentos.agents.state import AgentState
from investimentos.agents.schemas.portfolio_report import PortfolioReport
from investimentos.config import get_settings
from investimentos.llm.structured import chat_structured

ANALYSIS_PROMPT = """Você é um analista de carteira especializado em investimentos brasileiros.

Dados disponíveis (use APENAS campos presentes; não invente métricas ausentes):
{metrics_json}

Diretrizes:
- HHI ≥ 0.5 → "concentrada"; 0.2–0.5 → "moderada"; < 0.2 → "diversificada".
- drift severity: |delta_pct| ≤ 2 → "ok"; ≤ 7 → "atencao"; senão → "rebalancear".
- Cite ativos específicos quando disponíveis em `holdings_detail`.
- Sugira ações como "reduzir", "rebalancear", "revisar"; não emita compra/venda.
- Não mencione valores em R$.
"""


def _drop_nulls(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None and v != {} and v != []}


def portfolio_analyst_node(state: AgentState) -> dict:
    settings = get_settings()
    summary = state.portfolio_summary or {}

    if not summary or summary.get("source") == "empty":
        return {"portfolio_report": None}

    metrics = _drop_nulls({
        "allocation_pct": summary.get("allocation_pct"),
        "hhi": summary.get("hhi"),
        "max_drawdown_pct": summary.get("max_drawdown_pct"),
        "drift": summary.get("drift"),
        "holdings_detail": summary.get("holdings_detail"),
        "ticker_count": summary.get("ticker_count"),
        "source": summary.get("source"),
    })

    report = chat_structured(
        messages=[{
            "role": "user",
            "content": ANALYSIS_PROMPT.format(
                metrics_json=json.dumps(metrics, default=str, ensure_ascii=False),
            ),
        }],
        response_schema=PortfolioReport,
        model=settings.llm_model_default,
        max_tokens=1500,
    )
    return {"portfolio_report": report}
