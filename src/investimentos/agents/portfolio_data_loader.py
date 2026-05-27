"""Portfolio Data Loader — reads holdings from DB and populates portfolio_summary in state.

Priority order:
1. Compute holdings from TransactionRepository (most accurate — all history)
2. Fallback to PortfolioSnapshotRepository.get_latest() (from imported extrato)

Populates: allocation_pct, hhi, drift, source (transactions|snapshot|empty).
Market prices fetched via yfinance; falls back to avg_cost if unavailable.
BRL absolutes never written to state (privacy).
"""
from decimal import Decimal
from typing import Optional

from investimentos.agents.state import AgentState
from investimentos.config import get_settings
from investimentos.domain.db import engine_from_url
from sqlalchemy.orm import Session


def portfolio_data_loader_node(state: AgentState) -> dict:
    settings = get_settings()
    engine = engine_from_url(settings.database_url)
    account_id = state.account_id

    with Session(engine) as session:
        holdings = _load_from_transactions(session, account_id)
        source = "transactions"

        if not holdings:
            holdings = _load_from_snapshot(session, account_id)
            source = "snapshot" if holdings else "empty"

    if not holdings:
        return {"portfolio_summary": {"source": "empty", "allocation_pct": {}, "hhi": None}}

    prices = _fetch_prices([h["ticker"] for h in holdings])
    for h in holdings:
        h["current_price"] = prices.get(h["ticker"], h["avg_cost"])

    total_value = sum(h["qty"] * h["current_price"] for h in holdings)
    if total_value == 0:
        return {"portfolio_summary": {"source": source, "allocation_pct": {}, "hhi": None}}

    # allocation% per ticker (no BRL amounts in state)
    allocation_pct = {
        h["ticker"]: float(((h["qty"] * h["current_price"]) / total_value * 100).quantize(Decimal("0.01")))
        for h in holdings
    }

    # HHI — sum of squared weights (0 = diversified, 1 = concentrated)
    weights = [Decimal(str(v)) / Decimal("100") for v in allocation_pct.values()]
    hhi = float(sum(w ** 2 for w in weights).quantize(Decimal("0.0001")))

    # Drift vs active suggested portfolio class allocations
    drift = _compute_drift(session if False else None, holdings, allocation_pct, total_value, engine)

    return {
        "portfolio_summary": {
            "source": source,
            "allocation_pct": allocation_pct,
            "hhi": hhi,
            "drift": drift,
            "ticker_count": len(holdings),
        }
    }


def _load_from_transactions(session: Session, account_id: Optional[str]) -> list[dict]:
    from investimentos.repository.transaction import TransactionRepository
    from investimentos.repository.holding import HoldingComputer

    repo = TransactionRepository(session)
    computer = HoldingComputer(repo)
    holdings_objs = computer.compute_all(account_id=account_id)
    return [
        {"ticker": h.ticker, "qty": h.quantity, "avg_cost": h.average_cost}
        for h in holdings_objs
        if h.quantity > Decimal("0")
    ]


def _load_from_snapshot(session: Session, account_id: Optional[str]) -> list[dict]:
    from investimentos.repository.portfolio_snapshot_repo import PortfolioSnapshotRepository

    repo = PortfolioSnapshotRepository(session)
    snap = repo.get_latest(account_id or "")
    if snap is None:
        return []
    return [
        {
            "ticker": p.ticker,
            "qty": p.quantity,
            "avg_cost": p.avg_cost_hint or Decimal("0"),
        }
        for p in snap.equity_positions
        if p.quantity > Decimal("0")
    ]


def _fetch_prices(tickers: list[str]) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    try:
        from investimentos.integrations.yfinance_adapter import YFinanceClient
        yf = YFinanceClient()
        for ticker in tickers:
            try:
                q = yf.get_quote(f"{ticker}.SA")
                if q.get("price"):
                    prices[ticker] = Decimal(str(q["price"]))
            except Exception:
                pass
    except Exception:
        pass
    return prices


def _compute_drift(_, holdings: list[dict], allocation_pct: dict, total_value: Decimal, engine) -> dict:
    """Compute drift per asset class vs active SuggestedPortfolio."""
    from investimentos.tools.allocation_drift import compute_drift
    from investimentos.repository.suggested_portfolio_repo import SuggestedPortfolioRepository
    from investimentos.domain.models import AssetClass

    # Simple asset class mapping based on ticker suffix
    def _guess_class(ticker: str) -> str:
        t = ticker.upper()
        if t.endswith("11"):
            return AssetClass.FII.value if not t.startswith(("BOVA", "SMAL", "IVVB", "HASH")) else AssetClass.ETF.value
        return AssetClass.ACAO.value

    # Build actual class allocation from holdings
    class_values: dict[str, Decimal] = {}
    for h in holdings:
        cls = _guess_class(h["ticker"])
        v = h["qty"] * h.get("current_price", h["avg_cost"])
        class_values[cls] = class_values.get(cls, Decimal("0")) + v

    if total_value == 0:
        return {}

    actual_pct = {
        cls: (val / total_value * 100).quantize(Decimal("0.01"))
        for cls, val in class_values.items()
    }

    # Get target from active SuggestedPortfolio
    with Session(engine) as session:
        repo = SuggestedPortfolioRepository(session)
        # Get active portfolio to find class allocations target
        from investimentos.domain.db import SuggestedPortfolioORM
        active = session.query(SuggestedPortfolioORM).filter_by(status="active").first()
        if active is None:
            return {cls: {"actual_pct": float(pct), "target_pct": 0.0, "delta_pct": float(pct)} for cls, pct in actual_pct.items()}

        target_pct = {
            c["asset_class"]: Decimal(c["target_pct"])
            for c in (active.class_allocations_json or [])
        }

    raw_drift = compute_drift(actual_pct, target_pct)
    return {
        cls: {k: float(v) if isinstance(v, Decimal) else v for k, v in d.items()}
        for cls, d in raw_drift.items()
    }
