from decimal import Decimal
import pytest
from investimentos.tools.portfolio import (
    compute_average_cost, compute_twr, compute_dividend_yield, compute_contribution
)

def test_average_cost_single_purchase():
    transactions = [
        {"type": "compra", "qty": Decimal("100"), "price": Decimal("30.00"), "fees": Decimal("0")},
    ]
    assert compute_average_cost(transactions) == Decimal("30.0000")

def test_average_cost_two_purchases():
    transactions = [
        {"type": "compra", "qty": Decimal("100"), "price": Decimal("30.00"), "fees": Decimal("0")},
        {"type": "compra", "qty": Decimal("100"), "price": Decimal("40.00"), "fees": Decimal("0")},
    ]
    assert compute_average_cost(transactions) == Decimal("35.0000")

def test_average_cost_with_partial_sale():
    transactions = [
        {"type": "compra", "qty": Decimal("200"), "price": Decimal("30.00"), "fees": Decimal("0")},
        {"type": "venda", "qty": Decimal("100"), "price": Decimal("35.00"), "fees": Decimal("0")},
        {"type": "compra", "qty": Decimal("100"), "price": Decimal("40.00"), "fees": Decimal("0")},
    ]
    assert compute_average_cost(transactions) == Decimal("35.0000")

def test_twr_single_period():
    periods = [{"start_value": Decimal("1000"), "end_value": Decimal("1100"), "cashflows": Decimal("0")}]
    twr = compute_twr(periods)
    assert twr == pytest.approx(Decimal("10.00"), abs=Decimal("0.01"))

def test_dividend_yield():
    dividends = [Decimal("2.00"), Decimal("2.00"), Decimal("2.00"), Decimal("2.00")]
    avg_price = Decimal("40.00")
    dy = compute_dividend_yield(dividends, avg_price)
    assert dy == pytest.approx(Decimal("20.00"), abs=Decimal("0.01"))
