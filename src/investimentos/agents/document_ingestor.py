"""Document Ingestor — routes by detected document type."""
from pathlib import Path

from investimentos.agents.state import AgentState
from investimentos.integrations.documents.pdf_extractor import extract_pdf
from investimentos.integrations.documents.document_classifier import classify_document
from investimentos.integrations.documents.suggested_portfolio_parser import (
    parse_suggested_portfolio_with_fallback,
)
from investimentos.integrations.documents.extrato_parser import parse_extrato
from investimentos.integrations.documents.sanitizer import sanitize


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
        result = parse_extrato(sanitize(text))
        if result is None:
            return {"error": "Falha ao extrair transações do documento — formato não reconhecido"}
        transactions = result.get("transactions", [])
        equity_snapshot = result.get("equity_snapshot", [])
        fixed_income_snapshot = result.get("fixed_income_snapshot", [])
        period_end = result.get("period_end")
        return {
            "document_type": "transactions",
            "extracted_transactions": transactions,
            "extracted_snapshot": {
                "period_end": period_end,
                "equity_snapshot": equity_snapshot,
                "fixed_income_snapshot": fixed_income_snapshot,
            },
            "specialist_outputs": [
                f"## 📄 Extrato Processado\n\n"
                f"Período: `{period_end or 'desconhecido'}`\n\n"
                f"**{len(transactions)} transação(ões)** | "
                f"**{len(equity_snapshot)} posição(ões) em ações** | "
                f"**{len(fixed_income_snapshot)} posição(ões) em renda fixa**\n\n"
                f"Revise e confirme antes de importar."
            ],
        }

    return {
        "document_type": "unknown",
        "specialist_outputs": ["## ⚠️ Tipo de documento não reconhecido"],
    }
