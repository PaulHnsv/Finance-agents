from decimal import Decimal
from typing import TypedDict

DISCLAIMER = (
    "⚠️ Este relatório é meramente informativo e não constitui recomendação de investimento. "
    "Consulte um profissional habilitado pela CVM antes de tomar decisões de investimento."
)

class TxDict(TypedDict):
    type: str
    qty: Decimal
    price: Decimal
    fees: Decimal

class PeriodDict(TypedDict):
    start_value: Decimal
    end_value: Decimal
    cashflows: Decimal

def compute_average_cost(transactions: list[TxDict]) -> Decimal:
    total_qty = Decimal("0")
    total_cost = Decimal("0")
    for t in transactions:
        if t["type"] == "compra":
            total_cost += t["qty"] * t["price"] + t["fees"]
            total_qty += t["qty"]
        elif t["type"] == "venda" and total_qty > 0:
            avg = total_cost / total_qty
            total_cost -= t["qty"] * avg
            total_qty -= t["qty"]
    if total_qty == 0:
        return Decimal("0")
    return (total_cost / total_qty).quantize(Decimal("0.0001"))

def compute_twr(periods: list[PeriodDict]) -> Decimal:
    factor = Decimal("1")
    for p in periods:
        start = p["start_value"]
        if start == 0:
            continue
        period_return = (p["end_value"] - p["cashflows"]) / start
        factor *= period_return
    twr_pct = (factor - Decimal("1")) * Decimal("100")
    return twr_pct.quantize(Decimal("0.01"))

def compute_dividend_yield(dividends: list[Decimal], average_price: Decimal) -> Decimal:
    if average_price == 0:
        return Decimal("0")
    total = sum(dividends)
    return ((total / average_price) * Decimal("100")).quantize(Decimal("0.01"))

def compute_contribution(holdings: list[dict]) -> list[dict]:
    total = sum(h["market_value"] for h in holdings)
    if total == 0:
        return [{**h, "weight_pct": Decimal("0")} for h in holdings]
    return [
        {**h, "weight_pct": ((h["market_value"] / total) * 100).quantize(Decimal("0.01"))}
        for h in holdings
    ]
