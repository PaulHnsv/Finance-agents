from __future__ import annotations
from pydantic import BaseModel, Field


class TickerMovement(BaseModel):
    ticker: str
    change_pct: float
    comment: str = Field(max_length=180)


class MacroNote(BaseModel):
    topic: str = Field(max_length=80)
    comment: str = Field(max_length=240)


class MarketBrief(BaseModel):
    summary: str = Field(max_length=400)
    ticker_movements: list[TickerMovement] = Field(default_factory=list, max_length=10)
    macro_notes: list[MacroNote] = Field(default_factory=list, max_length=4)
    warnings: list[str] = Field(default_factory=list, max_length=3)
