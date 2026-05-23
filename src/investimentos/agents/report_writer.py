"""Report Writer — synthesizes specialist outputs into a final markdown report."""
from anthropic import Anthropic
from investimentos.agents.state import AgentState, DISCLAIMER
from investimentos.config import get_settings

REPORT_PROMPT = """Você é um redator de relatórios financeiros pessoais.

Com base nas análises dos especialistas abaixo, escreva um relatório final coerente, claro e organizado em markdown.

{specialist_outputs}

O relatório deve:
1. Ter um sumário executivo de 2-3 frases no topo
2. Organizar as seções de forma lógica
3. Destacar os 3 pontos de maior atenção
4. Ter uma seção "Próximos Passos" com 2-3 ações sugeridas

Use markdown com cabeçalhos, tópicos e destaques em negrito. Não repita o disclaimer — ele será adicionado automaticamente."""

def report_writer_node(state: AgentState) -> dict:
    if not state.specialist_outputs:
        return {"report_markdown": "Nenhuma análise disponível." + DISCLAIMER}

    settings = get_settings()
    combined = "\n\n---\n\n".join(state.specialist_outputs)

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.llm_model_default,
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": REPORT_PROMPT.format(specialist_outputs=combined),
        }],
    )
    report = response.content[0].text.strip() + DISCLAIMER
    return {"report_markdown": report}
