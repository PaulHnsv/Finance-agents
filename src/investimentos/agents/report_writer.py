"""Report Writer — pure renderer (no LLM)."""
from investimentos.agents.state import AgentState, DISCLAIMER
from investimentos.agents.rendering.report_renderer import render_full_report


def report_writer_node(state: AgentState) -> dict:
    if state.portfolio_report is None and state.market_brief is None and state.specialist_outputs:
        combined = "\n\n---\n\n".join(state.specialist_outputs)
        return {"report_markdown": combined + DISCLAIMER}
    rendered = render_full_report(
        portfolio_report=state.portfolio_report,
        market_brief=state.market_brief,
    )
    return {"report_markdown": rendered}
