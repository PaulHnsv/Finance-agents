"""Report Writer — pure renderer (no LLM)."""
from __future__ import annotations

from investimentos.agents.state import AgentState, DISCLAIMER
from investimentos.agents.rendering.report_renderer import render_full_report
from investimentos.agents.query_intent import (
    is_direct_holdings_question,
    requested_asset_class,
)

_ASSET_CLASS_LABELS = {
    "acao": "Ações",
    "fii": "Fundos imobiliários",
    "etf": "ETFs",
    "bdr": "BDRs",
    "renda_fixa": "Renda fixa",
}


def report_writer_node(state: AgentState) -> dict:
    direct_answer = _render_direct_holdings_answer(state)
    if direct_answer is not None:
        return {"report_markdown": direct_answer}

    if state.portfolio_report is None and state.market_brief is None and state.specialist_outputs:
        combined = "\n\n---\n\n".join(state.specialist_outputs)
        return {"report_markdown": combined + DISCLAIMER}
    rendered = render_full_report(
        portfolio_report=state.portfolio_report,
        market_brief=state.market_brief,
    )
    return {"report_markdown": rendered}


def _render_direct_holdings_answer(state: AgentState) -> str | None:
    if not is_direct_holdings_question(state.user_query):
        return None

    summary = state.portfolio_summary or {}
    holdings = summary.get("holdings_detail") or []
    requested_class = requested_asset_class(state.user_query)
    filtered_holdings = [
        h for h in holdings
        if requested_class is None or h.get("asset_class") == requested_class
    ]

    title_prefix = _ASSET_CLASS_LABELS.get(requested_class, "Ativos")
    lines = [f"# {title_prefix} na carteira", ""]
    if not filtered_holdings:
        lines.append(f"Não encontrei {title_prefix.lower()} na carteira com os dados disponíveis.")
        return "\n".join(lines) + DISCLAIMER

    for holding in sorted(filtered_holdings, key=lambda item: item.get("ticker", "")):
        ticker = holding.get("ticker", "Ativo")
        display_name = holding.get("display_name")
        allocation_pct = holding.get("allocation_pct")
        line = f"- **{ticker}**"
        if display_name and display_name != ticker:
            line += f" — {display_name}"
        if allocation_pct is not None:
            line += f" ({allocation_pct:.1f}% da carteira)"
        lines.append(line)

    return "\n".join(lines) + DISCLAIMER
