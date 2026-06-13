"""Deterministic query helpers shared by workflow nodes."""
from __future__ import annotations

import re
import unicodedata


_DIRECT_HOLDINGS_TERMS = (
    "quais",
    "qual",
    "listar",
    "liste",
    "mostre",
    "mostrar",
)

_HOLDINGS_OBJECT_TERMS = (
    "acao",
    "acoes",
    "ativo",
    "ativos",
    "papel",
    "papeis",
    "posicao",
    "posicoes",
    "fii",
    "fiis",
    "fundo imobiliario",
    "fundos imobiliarios",
    "etf",
    "etfs",
    "bdr",
    "bdrs",
    "renda fixa",
)

_TICKER_PATTERN = re.compile(r"\b[A-Z]{4}\d{1,2}\b")


def is_direct_holdings_question(query: str) -> bool:
    if _TICKER_PATTERN.search(query.upper()):
        return False

    normalized_query = normalize_text(query)
    return (
        any(_contains_word(normalized_query, term) for term in _DIRECT_HOLDINGS_TERMS)
        and any(term in normalized_query for term in _HOLDINGS_OBJECT_TERMS)
    )


def requested_asset_class(query: str) -> str | None:
    normalized_query = normalize_text(query)
    if "renda fixa" in normalized_query:
        return "renda_fixa"
    if "fundo imobiliario" in normalized_query or "fundos imobiliarios" in normalized_query:
        return "fii"
    for term, asset_class in (
        ("acoes", "acao"),
        ("acao", "acao"),
        ("fiis", "fii"),
        ("fii", "fii"),
        ("etfs", "etf"),
        ("etf", "etf"),
        ("bdrs", "bdr"),
        ("bdr", "bdr"),
    ):
        if term in normalized_query:
            return asset_class
    return None


def normalize_text(text: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(char)
    )
    return f" {without_accents} "


def _contains_word(normalized_query: str, term: str) -> bool:
    return f" {term} " in normalized_query
