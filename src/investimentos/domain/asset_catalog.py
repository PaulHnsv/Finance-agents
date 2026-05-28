"""Asset catalog — single source of truth for ticker classification."""
from __future__ import annotations
from typing import Literal, Optional, Protocol

from pydantic import BaseModel
from sqlalchemy.orm import Session

from investimentos.domain.models import AssetClass
from investimentos.domain.db import AssetORM
from investimentos.domain.ticker import normalize_b3_ticker, normalize_for_yfinance


class AssetClassification(BaseModel):
    ticker: str
    asset_class: AssetClass
    display_name: str
    sector: Optional[str] = None
    source: Literal["catalog", "yfinance", "heuristic"]


class _QuoteFetcher(Protocol):
    def get_quote(self, ticker: str) -> dict: ...


_ETF_PREFIXES = (
    "BOVA", "SMAL", "IVVB", "HASH", "SPXI", "GOLD",
    "DIVO", "FIND", "MATB", "BOVV", "ECOO", "ISUS",
)


class AssetCatalogService:
    """Resolves ticker -> AssetClassification: catalog -> yfinance -> heuristic."""

    def __init__(self, session: Session, yf_client: _QuoteFetcher):
        self._session = session
        self._yf = yf_client
        self._cache: dict[str, AssetClassification] = {}

    def classify(self, ticker: str) -> AssetClassification:
        t = normalize_b3_ticker(ticker)
        if t in self._cache:
            return self._cache[t]

        row = self._session.get(AssetORM, t)
        if row is not None:
            result = AssetClassification(
                ticker=t, asset_class=AssetClass(row.asset_class),
                display_name=row.name, source="catalog",
            )
            self._cache[t] = result
            return result

        if t.startswith(_ETF_PREFIXES):
            result = AssetClassification(
                ticker=t, asset_class=AssetClass.ETF,
                display_name=t, source="heuristic",
            )
            self._cache[t] = result
            return result

        try:
            q = self._yf.get_quote(normalize_for_yfinance(t))
            industry = (q.get("industry") or "").upper()
            name = q.get("name") or t
            if "REIT" in industry or "REAL ESTATE" in industry:
                cls = AssetClass.FII
            else:
                cls = AssetClass.ACAO
            result = AssetClassification(
                ticker=t, asset_class=cls,
                display_name=name, source="yfinance",
            )
            self._cache[t] = result
            return result
        except Exception:
            pass

        result = AssetClassification(
            ticker=t, asset_class=AssetClass.ACAO,
            display_name=t, source="heuristic",
        )
        self._cache[t] = result
        return result
