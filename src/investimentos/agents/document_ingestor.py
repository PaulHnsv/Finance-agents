"""
Document Ingestor — extracts transactions from documents.
Requires user confirmation before persisting.
"""
import json
from pathlib import Path
from anthropic import Anthropic
from investimentos.agents.state import AgentState
from investimentos.config import get_settings

EXTRACTION_PROMPT = """Você é um extrator de dados financeiros. Analise o texto abaixo de um documento financeiro e extraia as transações.

Texto do documento:
{text}

Retorne um JSON com a seguinte estrutura:
{{
  "document_type": "informe_rendimentos | nota_corretagem | extrato | outro",
  "transactions": [
    {{
      "date": "YYYY-MM-DD",
      "ticker": "XXXX3",
      "type": "compra | venda | dividendo | jcp",
      "quantity": 0.0,
      "price": 0.0,
      "fees": 0.0
    }}
  ]
}}

Se não encontrar transações, retorne "transactions": [].
Responda APENAS com JSON válido."""

def document_ingestor_node(state: AgentState) -> dict:
    if not state.document_path:
        return {"error": "Nenhum documento fornecido para ingestão"}

    path = Path(state.document_path)
    if not path.exists():
        return {"error": f"Arquivo não encontrado: {path}"}

    settings = get_settings()
    from investimentos.integrations.documents.pdf_extractor import extract_pdf
    text = extract_pdf(path)

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.llm_model_default,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(text=text[:8000]),
        }],
    )

    try:
        result = json.loads(response.content[0].text.strip())
        transactions = result.get("transactions", [])
    except json.JSONDecodeError:
        return {"error": "Falha ao extrair transações do documento — formato não reconhecido"}

    return {
        "extracted_transactions": transactions,
        "specialist_outputs": [
            f"## 📄 Documento Processado\n\n"
            f"Tipo: `{result.get('document_type', 'desconhecido')}`\n\n"
            f"**{len(transactions)} transação(ões) encontrada(s)**.\n\n"
            f"Revise e confirme antes de importar."
        ],
    }
