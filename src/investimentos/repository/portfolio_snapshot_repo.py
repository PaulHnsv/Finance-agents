"""Repository for PortfolioSnapshot: save, get_latest, get_equity_position, list_snapshots."""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from investimentos.domain.db import PortfolioSnapshotORM
from investimentos.domain.models import EquityPositionSnapshot, FixedIncomePosition, PortfolioSnapshot
from investimentos.repository.base import BaseRepository


class PortfolioSnapshotRepository(BaseRepository):
    def save(self, snap: PortfolioSnapshot) -> None:
        orm = PortfolioSnapshotORM(
            id=snap.id,
            account_id=snap.account_id,
            snapshot_date=snap.snapshot_date,
            source_file=snap.source_file,
            imported_at=snap.imported_at,
            equity_positions_json=[
                {
                    "ticker": p.ticker,
                    "quantity": str(p.quantity),
                    "avg_cost_hint": str(p.avg_cost_hint) if p.avg_cost_hint is not None else None,
                }
                for p in snap.equity_positions
            ],
            fixed_income_positions_json=[
                {
                    "name": fi.name,
                    "issuer": fi.issuer,
                    "maturity_date": fi.maturity_date.isoformat() if fi.maturity_date else None,
                    "invested_amount": str(fi.invested_amount),
                    "rate_description": fi.rate_description,
                    "current_value": str(fi.current_value),
                }
                for fi in snap.fixed_income_positions
            ],
        )
        self.session.merge(orm)
        self._commit()

    def get_latest(self, account_id: str) -> Optional[PortfolioSnapshot]:
        orm = (
            self.session.query(PortfolioSnapshotORM)
            .filter(PortfolioSnapshotORM.account_id == account_id)
            .order_by(PortfolioSnapshotORM.snapshot_date.desc())
            .first()
        )
        return self._to_domain(orm) if orm else None

    def get_equity_position(self, account_id: str, ticker: str) -> Optional[EquityPositionSnapshot]:
        snap = self.get_latest(account_id)
        if snap is None:
            return None
        ticker_upper = ticker.upper()
        for p in snap.equity_positions:
            if p.ticker == ticker_upper:
                return p
        return None

    def list_snapshots(self, account_id: str) -> list[PortfolioSnapshot]:
        orms = (
            self.session.query(PortfolioSnapshotORM)
            .filter(PortfolioSnapshotORM.account_id == account_id)
            .order_by(PortfolioSnapshotORM.snapshot_date)
            .all()
        )
        return [self._to_domain(o) for o in orms]

    def _to_domain(self, orm: PortfolioSnapshotORM) -> PortfolioSnapshot:
        equity = [
            EquityPositionSnapshot(
                ticker=p["ticker"],
                quantity=Decimal(p["quantity"]),
                avg_cost_hint=Decimal(p["avg_cost_hint"]) if p.get("avg_cost_hint") else None,
            )
            for p in (orm.equity_positions_json or [])
        ]
        fixed = [
            FixedIncomePosition(
                name=fi["name"],
                issuer=fi.get("issuer"),
                maturity_date=date.fromisoformat(fi["maturity_date"]) if fi.get("maturity_date") else None,
                invested_amount=Decimal(fi["invested_amount"]),
                rate_description=fi.get("rate_description"),
                current_value=Decimal(fi["current_value"]),
            )
            for fi in (orm.fixed_income_positions_json or [])
        ]
        return PortfolioSnapshot(
            id=orm.id,
            account_id=orm.account_id,
            snapshot_date=orm.snapshot_date,
            source_file=orm.source_file,
            imported_at=orm.imported_at,
            equity_positions=equity,
            fixed_income_positions=fixed,
        )
