"""Heuristic classifier: returns 'transactions', 'suggested_portfolio', or 'unknown'."""
import re

TXN_KEYWORDS = (
    "nota de corretagem", "liquidação", "compra de", "venda de", "d+2", "pregão",
)
SUGGESTION_KEYWORDS = (
    "portfólio sugerido", "carteira recomendada", "carteira sugerida",
    "alocação sugerida", "perfil moderado", "perfil arrojado",
    "perfil conservador", "perfil agressivo",
)
PCT_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s*%")


def classify_document(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    low = text.lower()
    txn_hits = sum(1 for kw in TXN_KEYWORDS if kw in low)
    sug_hits = sum(1 for kw in SUGGESTION_KEYWORDS if kw in low)
    pct_count = len(PCT_PATTERN.findall(text))
    if sug_hits >= 1 and pct_count >= 2 and txn_hits == 0:
        return "suggested_portfolio"
    if txn_hits >= 1:
        return "transactions"
    if sug_hits >= 1:
        return "suggested_portfolio"
    return "unknown"
