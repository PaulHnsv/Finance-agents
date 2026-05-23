from decimal import Decimal

def compute_drift(actual: dict[str, Decimal], target: dict[str, Decimal]) -> dict[str, dict]:
    all_classes = set(actual.keys()) | set(target.keys())
    return {
        cls: {
            "actual_pct": actual.get(cls, Decimal("0")),
            "target_pct": target.get(cls, Decimal("0")),
            "delta_pct": (actual.get(cls, Decimal("0")) - target.get(cls, Decimal("0"))).quantize(Decimal("0.01")),
        }
        for cls in all_classes
    }

def suggest_rebalance(actual: dict[str, Decimal], target: dict[str, Decimal], portfolio_value: Decimal) -> dict[str, dict]:
    drift = compute_drift(actual, target)
    suggestions = {}
    for cls, d in drift.items():
        delta = d["delta_pct"]
        amount = (abs(delta) / Decimal("100") * portfolio_value).quantize(Decimal("0.01"))
        if delta > Decimal("0"):
            action = "reduzir"
        elif delta < Decimal("0"):
            action = "aumentar"
        else:
            action = "manter"
        suggestions[cls] = {
            "action": action,
            "amount_brl": amount,
            "delta_pct": delta,
        }
    return suggestions
