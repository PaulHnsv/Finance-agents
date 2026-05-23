"""
Coordinator agent — classifies user intent and routes to specialists.
Only the query text is sent to the LLM (no financial data).
"""
from anthropic import Anthropic
from investimentos.agents.state import AgentState
from investimentos.config import get_settings

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

def coordinator_node(state: AgentState) -> dict:
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.llm_model_light,
        max_tokens=20,
        messages=[{
            "role": "user",
            "content": INTENT_PROMPT.format(query=state.user_query),
        }],
    )
    intent = response.content[0].text.strip().lower()
    valid_intents = {"portfolio_analysis", "market_query", "document_ingest", "report", "financial_planning", "other"}
    if intent not in valid_intents:
        intent = "other"
    return {"intent": intent}
