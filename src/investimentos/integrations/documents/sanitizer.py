"""Sanitize PII from financial document text before sending to LLM.

Masks CPF, CNPJ, phone numbers, emails, and monetary values in R$.
Preserves structure (tickers, dates, percentages) needed for extraction.
"""
import re

_RULES: list[tuple[re.Pattern, str]] = [
    # CPF: 000.000.000-00
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[CPF]"),
    # CNPJ: 00.000.000/0000-00
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "[CNPJ]"),
    # Phone: (00) 00000-0000 or (00) 0000-0000
    (re.compile(r"\(?\d{2}\)?\s*\d{4,5}[-\s]\d{4}\b"), "[TEL]"),
    # Email
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b"), "[EMAIL]"),
    # Monetary values: R$ 1.234,56 or R$1234.56
    (re.compile(r"R\$\s*[\d.,]+"), "R$[VALOR]"),
    # Large bare numbers likely to be account/agency numbers (6+ digits not part of a date/ticker)
    (re.compile(r"(?<!\d)(?<![A-Z])\d{6,}(?!\d)(?![A-Z])"), "[NUM]"),
]


def sanitize(text: str) -> str:
    """Apply all sanitization rules in order. Returns cleaned text."""
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text
