"""Shared LangGraph state schema for all agents."""
from __future__ import annotations
from typing import Annotated, Optional, Any
from pydantic import BaseModel
import operator

DISCLAIMER = (
    "\n\n---\n⚠️ **Aviso**: Este relatório é meramente informativo e não constitui "
    "recomendação de investimento regulada pela CVM. Consulte um profissional habilitado "
    "antes de tomar decisões de investimento."
)

class AgentState(BaseModel):
    """Shared state across all nodes in the portfolio query workflow."""
    user_query: str = ""
    account_id: Optional[str] = None
    intent: Optional[str] = None
    specialist_outputs: Annotated[list[str], operator.add] = []
    portfolio_summary: Optional[dict[str, Any]] = None
    market_data: Optional[dict[str, Any]] = None
    risk_metrics: Optional[dict[str, Any]] = None
    allocation_drift: Optional[dict[str, Any]] = None
    document_path: Optional[str] = None
    extracted_transactions: Optional[list[dict]] = None
    extracted_suggestion: Optional[dict] = None
    extracted_snapshot: Optional[dict] = None
    document_type: Optional[str] = None
    user_confirmed: bool = False
    report_markdown: Optional[str] = None
    error: Optional[str] = None
