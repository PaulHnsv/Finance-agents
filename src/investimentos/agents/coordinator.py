"""
Coordinator agent — classifies user intent and routes to specialists.
Only the query text is sent to the LLM (no financial data).
"""
from investimentos.agents.state import AgentState
from investimentos.config import get_settings
from investimentos.llm.client import chat

INTENT_PROMPT = """Você é o coordenador de um sistema de análise financeira pessoal.

Classifique a intenção do usuário em EXATAMENTE uma das categorias abaixo:
- portfolio_analysis: perguntas sobre carteira, posições, performance, risco, alocação
- market_query: perguntas sobre cotações, notícias, indicadores de ativos específicos
- document_ingest: o usuário quer importar um documento (PDF, OFX, CSV)
- report: o usuário quer um relatório completo da carteira
- financial_planning: perguntas sobre reserva de emergência, dívidas, fluxo de caixa
- other: não se encaixa nas categorias acima

Responda APENAS com a categoria, sem explicações.

Query do usuário: {query}"""

VALID_INTENTS = {
    "portfolio_analysis",
    "market_query",
    "document_ingest",
    "report",
    "financial_planning",
    "other",
}


def coordinator_node(state: AgentState) -> dict:
    settings = get_settings()
    raw = chat(
        messages=[{"role": "user", "content": INTENT_PROMPT.format(query=state.user_query)}],
        model=settings.llm_model_light,
        max_tokens=20,
    )
    intent = raw.strip().lower()
    if intent not in VALID_INTENTS:
        intent = "other"
    return {"intent": intent}
