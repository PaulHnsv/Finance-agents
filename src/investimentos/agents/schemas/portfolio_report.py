from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

from investimentos.domain.models import AssetClass


class DiversificationFinding(BaseModel):
    hhi: float
    classification: Literal["concentrada", "moderada", "diversificada"]
    comment: str = Field(max_length=240)


class DriftFinding(BaseModel):
    asset_class: AssetClass
    actual_pct: float
    target_pct: float
    delta_pct: float
    severity: Literal["ok", "atencao", "rebalancear"]
    comment: str = Field(max_length=180)


class RiskFinding(BaseModel):
    ticker: Optional[str] = None
    risk_type: Literal["concentracao", "drawdown", "liquidez", "setorial", "cambio"]
    description: str = Field(max_length=240)


class NextStep(BaseModel):
    action: str = Field(max_length=140)
    priority: Literal["alta", "media", "baixa"]
    rationale: str = Field(max_length=200)


class PortfolioReport(BaseModel):
    summary: str = Field(max_length=320)
    diversification: DiversificationFinding
    drift: list[DriftFinding] = Field(default_factory=list)
    risks: list[RiskFinding] = Field(default_factory=list, max_length=5)
    next_steps: list[NextStep] = Field(min_length=2, max_length=4)
    additional_notes: list[str] = Field(default_factory=list, max_length=3)
