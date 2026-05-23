from decimal import Decimal
import pytest
from investimentos.tools.risk import (
    compute_volatility_annualized, compute_max_drawdown, compute_herfindahl_index, compute_beta
)

def test_volatility_constant_returns_is_zero():
    daily_returns = [Decimal("0.001")] * 252
    vol = compute_volatility_annualized(daily_returns)
    assert vol == pytest.approx(Decimal("0"), abs=Decimal("0.0001"))

def test_volatility_positive():
    import random
    random.seed(42)
    returns = [Decimal(str(round(random.gauss(0.0005, 0.015), 6))) for _ in range(252)]
    vol = compute_volatility_annualized(returns)
    assert Decimal("0") < vol < Decimal("100")

def test_max_drawdown_flat():
    prices = [Decimal("100")] * 10
    assert compute_max_drawdown(prices) == Decimal("0")

def test_max_drawdown_decline_then_recover():
    prices = [Decimal("100"), Decimal("90"), Decimal("80"), Decimal("95"), Decimal("110")]
    dd = compute_max_drawdown(prices)
    assert dd == pytest.approx(Decimal("20.00"), abs=Decimal("0.01"))

def test_herfindahl_equal_weights():
    weights = [Decimal("0.25")] * 4
    hhi = compute_herfindahl_index(weights)
    assert hhi == pytest.approx(Decimal("0.25"), abs=Decimal("0.0001"))

def test_herfindahl_concentrated():
    weights = [Decimal("1.0"), Decimal("0.0"), Decimal("0.0")]
    hhi = compute_herfindahl_index(weights)
    assert hhi == Decimal("1.0000")

def test_beta_identical_returns():
    market = [Decimal("0.01"), Decimal("-0.01"), Decimal("0.02"), Decimal("-0.02")]
    asset = market.copy()
    beta = compute_beta(asset, market)
    assert beta == pytest.approx(Decimal("1.0"), abs=Decimal("0.001"))
