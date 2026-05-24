"""Extrato parser — single LLM call extracts transactions + position snapshot."""
import json
import re
from typing import Optional

from investimentos.config import get_settings
from investimentos.llm.client import chat

EXTRATO_PROMPT = """Extraia dados financeiros deste extrato de conta de investimento. Retorne JSON estrito.

Texto:
{text}

{{
  "period_end": "YYYY-MM-DD",
  "transactions": [
    {{"date":"YYYY-MM-DD","ticker":"XXXX4","type":"compra|venda","quantity":0.0,"price":0.0,"fees":0.0}}
  ],
  "equity_snapshot": [
    {{"ticker":"XXXX4","quantity":0.0,"avg_cost_hint":0.0}}
  ],
  "fixed_income_snapshot": [
    {{"name":"...","issuer":"...","maturity_date":"YYYY-MM-DD ou null",
      "invested_amount":0.0,"rate_description":"...","current_value":0.0}}
  ]
}}

Regras:
- transactions: apenas eventos COMPRA e VENDA do período (ações, ETFs, FIIs)
- equity_snapshot: posições em ações/ETFs/FIIs no final do período
- fixed_income_snapshot: CDBs, LCIs, LCAs, debêntures — sem ticker de bolsa
- avg_cost_hint pode ser null se não disponível
- Responda APENAS JSON, sem markdown."""

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def parse_extrato(text: str) -> Optional[dict]:
    """Call LLM to extract transactions + position snapshot from extrato text.

    Returns dict with keys: period_end, transactions, equity_snapshot, fixed_income_snapshot.
    Returns None if LLM response cannot be parsed as JSON.
    """
    settings = get_settings()
    raw = chat(
        messages=[{"role": "user", "content": EXTRATO_PROMPT.format(text=text[:8000])}],
        model=settings.llm_model_default,
        max_tokens=2048,
    )
    cleaned = _FENCE_RE.sub("", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None
