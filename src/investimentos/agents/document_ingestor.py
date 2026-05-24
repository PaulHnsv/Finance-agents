"""Document Ingestor — routes by detected document type."""
import json
import re
from pathlib import Path

from investimentos.agents.state import AgentState
from investimentos.config import get_settings
from investimentos.integrations.documents.pdf_extractor import extract_pdf
from investimentos.integrations.documents.document_classifier import classify_document
from investimentos.integrations.documents.suggested_portfolio_parser import (
    parse_suggested_portfolio_with_fallback,
)
from investimentos.llm.client import chat


EXTRACTION_PROMPT = """Você é um extrator de dados financeiros. Analise o texto abaixo e extraia as transações.

Texto:
{text}

Retorne JSON:
{{
  "document_type": "nota_corretagem|informe|extrato|outro",
  "transactions": [{{"date":"YYYY-MM-DD","ticker":"XXXX4","type":"compra|venda|dividendo|jcp","quantity":0.0,"price":0.0,"fees":0.0}}]
}}
Responda APENAS JSON."""

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _strip_fences(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


def _extract_transactions(text: str) -> dict | None:
    settings = get_settings()
    raw = chat(
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=text[:8000])}],
        model=settings.llm_model_default,
        max_tokens=2048,
    )
    try:
        return json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return None


def document_ingestor_node(state: AgentState) -> dict:
    if not state.document_path:
        return {"error": "Nenhum documento fornecido para ingestão"}
    path = Path(state.document_path)
    if not path.exists():
        return {"error": f"Arquivo não encontrado: {path}"}

    text = extract_pdf(path)
    doc_type = classify_document(text)

    if doc_type == "suggested_portfolio":
        suggestion = parse_suggested_portfolio_with_fallback(text)
        return {
            "document_type": "suggested_portfolio",
            "extracted_suggestion": suggestion,
            "specialist_outputs": [
                f"## 📄 Carteira Sugerida Detectada\n\n"
                f"- {len(suggestion['class_allocations'])} classe(s) de ativo\n"
                f"- {len(suggestion['asset_allocations'])} ativo(s)\n\n"
                f"Revise e confirme antes de salvar."
            ],
        }

    if doc_type == "transactions":
        result = _extract_transactions(text)
        if result is None:
            return {"error": "Falha ao extrair transações do documento — formato não reconhecido"}
        transactions = result.get("transactions", [])
        return {
            "document_type": "transactions",
            "extracted_transactions": transactions,
            "specialist_outputs": [
                f"## 📄 Documento Processado\n\n"
                f"Tipo: `{result.get('document_type', 'desconhecido')}`\n\n"
                f"**{len(transactions)} transação(ões) encontrada(s)**.\n\n"
                f"Revise e confirme antes de importar."
            ],
        }

    return {
        "document_type": "unknown",
        "specialist_outputs": ["## ⚠️ Tipo de documento não reconhecido"],
    }
