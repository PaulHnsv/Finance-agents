"""
Portfolio Analyst — computes portfolio metrics deterministically, then asks
the LLM to synthesize and explain the results. BRL absolutes never sent to LLM.
"""
import json

from investimentos.agents.state import AgentState, DISCLAIMER
from investimentos.config import get_settings
from investimentos.llm.client import chat

ANALYSIS_PROMPT = """Você é um analista de carteira especializado em investimentos brasileiros.

Com base nas métricas calculadas abaixo (valores em % e métricas relativas — sem valores absolutos em R$ por privacidade), forneça uma análise clara e objetiva:

{metrics_json}

Inclua na sua análise:
1. Avaliação da diversificação (HHI: 0 = totalmente diversificado, 1 = concentrado)
2. Principais riscos identificados
3. Comentário sobre o drift em relação ao target
4. Pontos de atenção

Seja conciso (máx. 300 palavras). Use tópicos onde apropriado. Não mencione valores em R$."""


def portfolio_analyst_node(state: AgentState) -> dict:
    settings = get_settings()
    summary = state.portfolio_summary or {}
    metrics = {
        "allocation_pct": summary.get("allocation_pct", {}),
        "hhi": summary.get("hhi"),
        "max_drawdown_pct": summary.get("max_drawdown_pct"),
        "twr_pct": summary.get("twr_pct"),
        "drift": summary.get("drift", {}),
    }
    analysis = chat(
        messages=[{
            "role": "user",
            "content": ANALYSIS_PROMPT.format(
                metrics_json=json.dumps(metrics, default=str, ensure_ascii=False),
            ),
        }],
        model=settings.llm_model_default,
        max_tokens=600,
    )
    output = f"## 📊 Análise de Carteira\n\n{analysis}{DISCLAIMER}"
    return {"specialist_outputs": [output]}
