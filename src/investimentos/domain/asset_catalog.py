"""Asset catalog — single source of truth for ticker classification."""
from __future__ import annotations
from typing import Literal, Optional

from pydantic import BaseModel

from investimentos.domain.models import AssetClass


class AssetClassification(BaseModel):
    ticker: str
    asset_class: AssetClass
    display_name: str
    sector: Optional[str] = None
    source: Literal["catalog", "yfinance", "heuristic"]
