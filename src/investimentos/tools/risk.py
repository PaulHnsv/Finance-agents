from decimal import Decimal
import math
from typing import Sequence

def compute_volatility_annualized(daily_returns: Sequence[Decimal]) -> Decimal:
    n = len(daily_returns)
    if n < 2:
        return Decimal("0")
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / (n - 1)
    daily_std = Decimal(str(math.sqrt(float(variance))))
    annualized = daily_std * Decimal(str(math.sqrt(252))) * Decimal("100")
    return annualized.quantize(Decimal("0.0001"))

def compute_max_drawdown(prices: Sequence[Decimal]) -> Decimal:
    if len(prices) < 2:
        return Decimal("0")
    peak = prices[0]
    max_dd = Decimal("0")
    for price in prices:
        if price > peak:
            peak = price
        dd = (peak - price) / peak * Decimal("100")
        if dd > max_dd:
            max_dd = dd
    return max_dd.quantize(Decimal("0.01"))

def compute_herfindahl_index(weights: Sequence[Decimal]) -> Decimal:
    return sum(w ** 2 for w in weights).quantize(Decimal("0.0001"))

def compute_beta(asset_returns: Sequence[Decimal], market_returns: Sequence[Decimal]) -> Decimal:
    n = len(asset_returns)
    if n < 2 or n != len(market_returns):
        return Decimal("1")
    mean_a = sum(asset_returns) / n
    mean_m = sum(market_returns) / n
    covariance = sum((asset_returns[i] - mean_a) * (market_returns[i] - mean_m) for i in range(n))
    variance_m = sum((r - mean_m) ** 2 for r in market_returns)
    if variance_m == 0:
        return Decimal("1")
    return (covariance / variance_m).quantize(Decimal("0.0001"))
