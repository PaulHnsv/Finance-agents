from decimal import Decimal
import pytest
from investimentos.tools.allocation_drift import compute_drift, suggest_rebalance

def test_compute_drift_no_gap():
    actual = {"acao": Decimal("60"), "renda_fixa": Decimal("40")}
    target = {"acao": Decimal("60"), "renda_fixa": Decimal("40")}
    drift = compute_drift(actual, target)
    assert drift["acao"]["delta_pct"] == Decimal("0")

def test_compute_drift_with_gap():
    actual = {"acao": Decimal("70"), "renda_fixa": Decimal("30")}
    target = {"acao": Decimal("60"), "renda_fixa": Decimal("40")}
    drift = compute_drift(actual, target)
    assert drift["acao"]["delta_pct"] == Decimal("10.00")
    assert drift["renda_fixa"]["delta_pct"] == Decimal("-10.00")

def test_suggest_rebalance_total_portfolio():
    actual = {"acao": Decimal("70"), "renda_fixa": Decimal("30")}
    target = {"acao": Decimal("60"), "renda_fixa": Decimal("40")}
    portfolio_value = Decimal("100000")
    suggestions = suggest_rebalance(actual, target, portfolio_value)
    assert suggestions["acao"]["action"] == "reduzir"
    assert suggestions["acao"]["amount_brl"] == Decimal("10000.00")
    assert suggestions["renda_fixa"]["action"] == "aumentar"
    assert suggestions["renda_fixa"]["amount_brl"] == Decimal("10000.00")
