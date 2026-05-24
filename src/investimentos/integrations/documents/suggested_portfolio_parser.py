"""Regex-first parser for 'carteira sugerida' documents. LLM fallback when regex finds nothing."""
import json
import re
from decimal import Decimal

from investimentos.config import get_settings
from investimentos.llm.client import chat


CLASS_ALIASES = {
    "ações brasil": "acao", "acoes brasil": "acao", "ações br": "acao",
    "ações": "acao", "acoes": "acao",
    "renda fixa": "renda_fixa",
    "internacional": "etf", "exterior": "etf",
    "fii": "fii", "fiis": "fii", "fundos imobiliários": "fii",
    "etf": "etf", "etfs": "etf",
    "tesouro": "tesouro", "tesouro direto": "tesouro",
    "caixa": "caixa",
    "fundo": "fundo", "fundos": "fundo",
    "bdr": "bdr", "bdrs": "bdr",
}

_TICKER_RE = re.compile(
    r"\b([A-Z]{4}\d{1,2})\b\s*[—\-:]?\s*(\d+(?:[.,]\d+)?)\s*%\s*[—\-:]?\s*(.*)"
)
_CLASS_LINE_RE = re.compile(
    r"^\s*([A-Za-zÀ-ÿ ]+?)\s*[:\-]\s*(\d+(?:[.,]\d+)?)\s*%\s*$",
    re.MULTILINE,
)


def _to_decimal(s: str) -> Decimal:
    return Decimal(s.replace(",", "."))


def parse_suggested_portfolio(text: str) -> dict:
    class_allocs = []
    for m in _CLASS_LINE_RE.finditer(text):
        label = m.group(1).strip().lower()
        if label in CLASS_ALIASES:
            class_allocs.append({
                "asset_class": CLASS_ALIASES[label],
                "target_pct": _to_decimal(m.group(2)),
            })

    asset_allocs = []
    for line in text.splitlines():
        m = _TICKER_RE.search(line)
        if not m:
            continue
        ticker, pct, rest = m.group(1), m.group(2), (m.group(3) or "").strip()
        asset_allocs.append({
            "ticker": ticker.upper(),
            "target_pct": _to_decimal(pct),
            "thesis": rest[:200] if rest else None,
        })
    return {"class_allocations": class_allocs, "asset_allocations": asset_allocs}


_LLM_PROMPT = """Extraia alocação sugerida em JSON estrito.
Texto:
{text}

Schema:
{{"class_allocations":[{{"asset_class":"acao|fii|etf|renda_fixa|tesouro|fundo|bdr|caixa","target_pct":number}}],
  "asset_allocations":[{{"ticker":"XXXX4","target_pct":number,"thesis":"string ou null"}}]}}

Se nada extraível, retorne listas vazias. Responda APENAS JSON."""


def _llm_extract(text: str) -> dict:
    settings = get_settings()
    raw = chat(
        messages=[{"role": "user", "content": _LLM_PROMPT.format(text=text[:8000])}],
        model=settings.llm_model_default,
        max_tokens=2048,
    )
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)
    for c in data.get("class_allocations", []):
        c["target_pct"] = Decimal(str(c["target_pct"]))
    for a in data.get("asset_allocations", []):
        a["target_pct"] = Decimal(str(a["target_pct"]))
    return data


def parse_suggested_portfolio_with_fallback(text: str) -> dict:
    result = parse_suggested_portfolio(text)
    if not result["class_allocations"] and not result["asset_allocations"]:
        try:
            return _llm_extract(text)
        except Exception:
            return result
    return result
