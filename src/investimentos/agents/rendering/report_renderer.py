"""Pure-Python renderers — no LLM calls. Schema → markdown."""
from __future__ import annotations
from typing import Optional

from investimentos.agents.state import DISCLAIMER
from investimentos.agents.schemas.portfolio_report import PortfolioReport
from investimentos.agents.schemas.market_brief import MarketBrief

_SEVERITY_ICON = {"ok": "✅", "atencao": "⚠️", "rebalancear": "🔴"}
_PRIORITY_ICON = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}


def render_portfolio_report(r: PortfolioReport) -> str:
    lines: list[str] = ["# 📊 Relatório da Carteira", ""]
    lines.append("## Sumário")
    lines.append(r.summary)
    lines.append("")
    lines.append("## Diversificação")
    lines.append(
        f"- **HHI**: {r.diversification.hhi:.2f} "
        f"(classificação: **{r.diversification.classification}**)"
    )
    lines.append(f"- {r.diversification.comment}")
    lines.append("")
    if r.drift:
        lines.append("## Drift de Alocação")
        for d in r.drift:
            icon = _SEVERITY_ICON.get(d.severity, "•")
            lines.append(
                f"- {icon} **{d.asset_class.value}** — atual {d.actual_pct:.1f}%, "
                f"target {d.target_pct:.1f}% (Δ {d.delta_pct:+.1f}%): {d.comment}"
            )
        lines.append("")
    if r.risks:
        lines.append("## Riscos")
        for rk in r.risks:
            label = f"{rk.ticker} — " if rk.ticker else ""
            lines.append(f"- **{label}{rk.risk_type}**: {rk.description}")
        lines.append("")
    lines.append("## Próximos Passos")
    for s in r.next_steps:
        icon = _PRIORITY_ICON.get(s.priority, "•")
        lines.append(f"- {icon} **{s.action}** ({s.priority}) — {s.rationale}")
    if r.additional_notes:
        lines.append("")
        lines.append("## Notas Adicionais")
        for n in r.additional_notes:
            lines.append(f"- {n}")
    return "\n".join(lines)


def render_market_brief(b: MarketBrief) -> str:
    lines: list[str] = ["# 📈 Cenário de Mercado", "", b.summary, ""]
    if b.ticker_movements:
        lines.append("## Movimentos")
        for m in b.ticker_movements:
            lines.append(f"- **{m.ticker}** ({m.change_pct:+.2f}%): {m.comment}")
        lines.append("")
    if b.macro_notes:
        lines.append("## Macro")
        for n in b.macro_notes:
            lines.append(f"- **{n.topic}**: {n.comment}")
        lines.append("")
    if b.warnings:
        lines.append("## Atenção")
        for w in b.warnings:
            lines.append(f"- {w}")
    return "\n".join(lines)


def render_full_report(
    *,
    portfolio_report: Optional[PortfolioReport],
    market_brief: Optional[MarketBrief],
) -> str:
    sections: list[str] = []
    if portfolio_report is not None:
        sections.append(render_portfolio_report(portfolio_report))
    if market_brief is not None:
        sections.append(render_market_brief(market_brief))
    if not sections:
        return "Nenhuma análise disponível." + DISCLAIMER
    return "\n\n---\n\n".join(sections) + DISCLAIMER
