from decimal import Decimal
from typing import Optional
from investimentos.domain.models import Holding, Transaction, TransactionType
from investimentos.repository.transaction import TransactionRepository

class HoldingComputer:
    """Derives Holding positions from transactions. Never stores computed state."""

    def __init__(self, transaction_repo: TransactionRepository):
        self.repo = transaction_repo

    def compute(self, ticker: str, account_id: Optional[str] = None, current_price: Decimal = Decimal("0")) -> list[Holding]:
        txns = self.repo.list_by_ticker(ticker, account_id)
        by_account: dict[str, list[Transaction]] = {}
        for t in txns:
            by_account.setdefault(t.account_id, []).append(t)

        result = []
        for acc_id, acc_txns in by_account.items():
            total_qty = Decimal("0")
            total_cost = Decimal("0")
            for t in acc_txns:
                if t.transaction_type == TransactionType.COMPRA:
                    total_cost += t.quantity * t.unit_price + t.fees
                    total_qty += t.quantity
                elif t.transaction_type == TransactionType.VENDA:
                    if total_qty > 0:
                        avg = total_cost / total_qty
                        total_cost -= t.quantity * avg
                        total_qty -= t.quantity
            if total_qty > Decimal("0"):
                avg_cost = (total_cost / total_qty).quantize(Decimal("0.0001"))
                result.append(Holding(
                    ticker=ticker,
                    account_id=acc_id,
                    quantity=total_qty,
                    average_cost=avg_cost,
                    current_price=current_price,
                ))
        return result

    def compute_all(self, account_id: Optional[str] = None, prices: dict[str, Decimal] = None) -> list[Holding]:
        prices = prices or {}
        tickers = self.repo.distinct_tickers(account_id)
        result = []
        for ticker in tickers:
            result.extend(self.compute(ticker, account_id, prices.get(ticker, Decimal("0"))))
        return result
