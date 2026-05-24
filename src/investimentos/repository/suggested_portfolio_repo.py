"""Repository for SuggestedPortfolio: save, get, activate (archives previous active), get_thesis_for."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from investimentos.domain.db import SuggestedPortfolioORM
from investimentos.domain.models import (
    AssetClass,
    RiskProfile,
    SuggestedAssetAllocation,
    SuggestedClassAllocation,
    SuggestedPortfolio,
    SuggestedPortfolioStatus,
)


def _to_orm(sp: SuggestedPortfolio) -> SuggestedPortfolioORM:
    return SuggestedPortfolioORM(
        id=sp.id,
        name=sp.name,
        source_file=sp.source_file,
        risk_profile_hint=sp.risk_profile_hint.value if sp.risk_profile_hint else None,
        status=sp.status.value,
        class_allocations_json=[
            {"asset_class": c.asset_class.value, "target_pct": str(c.target_pct)}
            for c in sp.class_allocations
        ],
        asset_allocations_json=[
            {"ticker": a.ticker, "target_pct": str(a.target_pct), "thesis": a.thesis}
            for a in sp.asset_allocations
        ],
        imported_at=sp.imported_at,
        activated_at=sp.activated_at,
    )


def _from_orm(orm: SuggestedPortfolioORM) -> SuggestedPortfolio:
    return SuggestedPortfolio(
        id=orm.id,
        name=orm.name,
        source_file=orm.source_file,
        risk_profile_hint=RiskProfile(orm.risk_profile_hint) if orm.risk_profile_hint else None,
        status=SuggestedPortfolioStatus(orm.status),
        class_allocations=[
            SuggestedClassAllocation(
                asset_class=AssetClass(c["asset_class"]),
                target_pct=Decimal(c["target_pct"]),
            )
            for c in (orm.class_allocations_json or [])
        ],
        asset_allocations=[
            SuggestedAssetAllocation(
                ticker=a["ticker"],
                target_pct=Decimal(a["target_pct"]),
                thesis=a.get("thesis"),
            )
            for a in (orm.asset_allocations_json or [])
        ],
        imported_at=orm.imported_at,
        activated_at=orm.activated_at,
    )


class SuggestedPortfolioRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, sp: SuggestedPortfolio) -> None:
        self.session.merge(_to_orm(sp))
        self.session.commit()

    def get(self, sp_id: str) -> Optional[SuggestedPortfolio]:
        orm = self.session.get(SuggestedPortfolioORM, sp_id)
        return _from_orm(orm) if orm else None

    def activate(self, sp_id: str) -> None:
        for orm in self.session.query(SuggestedPortfolioORM).filter_by(status="active").all():
            orm.status = "archived"
        target = self.session.get(SuggestedPortfolioORM, sp_id)
        if not target:
            raise ValueError(f"SuggestedPortfolio {sp_id} not found")
        target.status = "active"
        target.activated_at = datetime.utcnow()
        self.session.commit()

    def get_thesis_for(self, ticker: str) -> Optional[str]:
        ticker = ticker.upper()
        active = self.session.query(SuggestedPortfolioORM).filter_by(status="active").first()
        if not active:
            return None
        for a in active.asset_allocations_json or []:
            if a["ticker"] == ticker:
                return a.get("thesis")
        return None
