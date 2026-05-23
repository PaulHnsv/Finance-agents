from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from investimentos.domain.db import TransactionORM
from investimentos.domain.models import Transaction, TransactionType
from investimentos.repository.base import BaseRepository

class TransactionRepository(BaseRepository):
    def save(self, transaction: Transaction) -> None:
        orm = TransactionORM(
            id=transaction.id,
            account_id=transaction.account_id,
            ticker=transaction.ticker.upper(),
            transaction_type=transaction.transaction_type.value,
            quantity=transaction.quantity,
            unit_price=transaction.unit_price,
            date=transaction.date,
            fees=transaction.fees,
            irrf=transaction.irrf,
            notes=transaction.notes,
        )
        self.session.merge(orm)
        self._commit()

    def list_by_ticker(self, ticker: str, account_id: Optional[str] = None) -> list[Transaction]:
        q = self.session.query(TransactionORM).filter(
            TransactionORM.ticker == ticker.upper()
        )
        if account_id:
            q = q.filter(TransactionORM.account_id == account_id)
        q = q.order_by(TransactionORM.date)
        return [self._to_domain(o) for o in q.all()]

    def list_all(self, account_id: Optional[str] = None) -> list[Transaction]:
        q = self.session.query(TransactionORM)
        if account_id:
            q = q.filter(TransactionORM.account_id == account_id)
        return [self._to_domain(o) for o in q.order_by(TransactionORM.date).all()]

    def distinct_tickers(self, account_id: Optional[str] = None) -> list[str]:
        q = self.session.query(TransactionORM.ticker).distinct()
        if account_id:
            q = q.filter(TransactionORM.account_id == account_id)
        return [r[0] for r in q.all()]

    def _to_domain(self, orm: TransactionORM) -> Transaction:
        return Transaction(
            id=orm.id,
            account_id=orm.account_id,
            ticker=orm.ticker,
            transaction_type=TransactionType(orm.transaction_type),
            quantity=Decimal(str(orm.quantity)),
            unit_price=Decimal(str(orm.unit_price)),
            date=orm.date,
            fees=Decimal(str(orm.fees or 0)),
            irrf=Decimal(str(orm.irrf or 0)),
            notes=orm.notes,
        )
