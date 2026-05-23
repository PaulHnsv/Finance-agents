from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from investimentos.domain.db import AccountORM
from investimentos.domain.models import Account, AccountType
from investimentos.repository.base import BaseRepository

class AccountRepository(BaseRepository):
    def save(self, account: Account) -> None:
        orm = AccountORM(
            id=account.id,
            name=account.name,
            account_type=account.account_type.value,
            custodian=account.custodian,
            brokerage_fee_pct=account.brokerage_fee_pct,
        )
        self.session.merge(orm)
        self._commit()

    def get_by_id(self, account_id: str) -> Optional[Account]:
        orm = self.session.get(AccountORM, account_id)
        if orm is None:
            return None
        return Account(
            id=orm.id,
            name=orm.name,
            account_type=AccountType(orm.account_type),
            custodian=orm.custodian,
            brokerage_fee_pct=Decimal(str(orm.brokerage_fee_pct or 0)),
        )

    def list_all(self) -> list[Account]:
        orms = self.session.query(AccountORM).all()
        return [self.get_by_id(o.id) for o in orms]
