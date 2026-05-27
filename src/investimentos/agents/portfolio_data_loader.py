"""Portfolio Data Loader — reads holdings from DB and populates portfolio_summary in state.

Priority order:
1. Compute holdings from TransactionRepository (most accurate — all history)
2. Fallback to PortfolioSnapshotRepository.get_latest() (from imported extrato)

Populates: allocation_pct, hhi, drift, max_drawdown_pct, source (transactions|snapshot|empty).
Market prices fetched via yfinance; falls back to avg_cost if unavailable.
BRL absolutes never written to state (privacy).
"""
from decimal import Decimal
from typing import Optional

from investimentos.agents.state import AgentState
from investimentos.config import get_settings
from investimentos.domain.db import engine_from_url
from investimentos.integrations.yfinance_adapter import YFinanceClient
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

        # Fixed income from snapshot is always loaded (even when equity comes from transactions)
        fi_total = _load_fi_total_from_snapshot(session, account_id)

    if not holdings and fi_total == 0:
        return {"portfolio_summary": {"source": "empty", "allocation_pct": {}, "hhi": None}}

    quotes = _fetch_quotes([h["ticker"] for h in holdings])
    for h in holdings:
        h["current_price"] = quotes.get(h["ticker"], {}).get("price", h["avg_cost"])

    equity_value = sum(h["qty"] * h["current_price"] for h in holdings)
    total_value = equity_value + fi_total
    if total_value == 0:
        return {"portfolio_summary": {"source": source, "allocation_pct": {}, "hhi": None}}

    # allocation% per ticker for equity (no BRL amounts in state)
    allocation_pct: dict[str, float] = {
        h["ticker"]: float(((h["qty"] * h["current_price"]) / total_value * 100).quantize(Decimal("0.01")))
        for h in holdings
    }
    if fi_total > 0:
        allocation_pct["renda_fixa"] = float((fi_total / total_value * 100).quantize(Decimal("0.01")))

    # HHI — computed on equity tickers only (FI is a single bucket)
    equity_pct = {k: v for k, v in allocation_pct.items() if k != "renda_fixa"}
    weights = [Decimal(str(v)) / Decimal("100") for v in equity_pct.values()]
    hhi = float(sum(w ** 2 for w in weights).quantize(Decimal("0.0001"))) if weights else None

    drift = _compute_drift(None, holdings, allocation_pct, total_value, engine, quotes, fi_total)

    return {
        "portfolio_summary": {
            "source": source,
            "allocation_pct": allocation_pct,
            "hhi": hhi,
            "drift": drift,
            "max_drawdown_pct": _compute_portfolio_max_drawdown(holdings, equity_pct),
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


def _load_fi_total_from_snapshot(session: Session, account_id: Optional[str]) -> Decimal:
    """Returns total current value of fixed income positions from latest snapshot."""
    from investimentos.repository.portfolio_snapshot_repo import PortfolioSnapshotRepository

    repo = PortfolioSnapshotRepository(session)
    snap = repo.get_latest(account_id or "")
    if snap is None:
        return Decimal("0")
    return sum((fi.current_value for fi in snap.fixed_income_positions), Decimal("0"))


def _fetch_quotes(tickers: list[str]) -> dict[str, dict]:
    """Fetch price + metadata (industry, quote_type) for each ticker.

    Returns {ticker: {"price": Decimal, "industry": str, "quote_type": str}}.
    """
    result: dict[str, dict] = {}
    try:
        yf_client = YFinanceClient()
        for ticker in tickers:
            try:
                q = yf_client.get_quote(f"{ticker}.SA")
                result[ticker] = {
                    "price": q.get("price", Decimal("0")),
                    "industry": q.get("industry", ""),
                    "quote_type": q.get("quote_type", ""),
                }
            except Exception:
                result[ticker] = {"price": Decimal("0"), "industry": "", "quote_type": ""}
    except Exception:
        pass
    return result


def _compute_drift(
    _,
    holdings: list[dict],
    allocation_pct: dict,
    total_value: Decimal,
    engine,
    quotes: dict,
    fi_total: Decimal,
) -> dict:
    """Compute drift per asset class vs active SuggestedPortfolio."""
    from investimentos.tools.allocation_drift import compute_drift
    from investimentos.domain.models import AssetClass

    ETF_PREFIXES = ("BOVA", "SMAL", "IVVB", "HASH", "SPXI", "GOLD", "DIVO", "FIND", "MATB")

    def _guess_class(ticker: str) -> str:
        t = ticker.upper()
        if t.startswith(ETF_PREFIXES):
            return AssetClass.ETF.value
        meta = quotes.get(ticker, {})
        ind = meta.get("industry", "").upper()
        qt = meta.get("quote_type", "").upper()
        # yfinance marks Brazilian FIIs as ETF with REIT in industry
        if "REIT" in ind or "REAL ESTATE" in ind:
            return AssetClass.FII.value
        if qt == "ETF" and t.endswith("11") and not t.startswith(ETF_PREFIXES):
            return AssetClass.FII.value
        # Conservative default: tickers ending in "11" without REIT confirmation → ACAO
        # (covers units like ALUP11, KLBN11 that are stocks, not FIIs)
        return AssetClass.ACAO.value

    class_values: dict[str, Decimal] = {}
    for h in holdings:
        cls = _guess_class(h["ticker"])
        v = h["qty"] * h.get("current_price", h["avg_cost"])
        class_values[cls] = class_values.get(cls, Decimal("0")) + v

    if fi_total > 0:
        class_values[AssetClass.RENDA_FIXA.value] = (
            class_values.get(AssetClass.RENDA_FIXA.value, Decimal("0")) + fi_total
        )

    if total_value == 0:
        return {}

    actual_pct = {
        cls: (val / total_value * 100).quantize(Decimal("0.01"))
        for cls, val in class_values.items()
    }

    with Session(engine) as session:
        from investimentos.domain.db import SuggestedPortfolioORM
        active = session.query(SuggestedPortfolioORM).filter_by(status="active").first()
        if active is None:
            return {
                cls: {"actual_pct": float(pct), "target_pct": 0.0, "delta_pct": float(pct)}
                for cls, pct in actual_pct.items()
            }
        target_pct = {
            c["asset_class"]: Decimal(c["target_pct"])
            for c in (active.class_allocations_json or [])
        }

    raw_drift = compute_drift(actual_pct, target_pct)
    return {
        cls: {k: float(v) if isinstance(v, Decimal) else v for k, v in d.items()}
        for cls, d in raw_drift.items()
    }


def _compute_portfolio_max_drawdown(holdings: list[dict], allocation_pct: dict) -> Optional[float]:
    """Compute weighted portfolio max drawdown using 1-year price history from yfinance.

    Returns the max drawdown % as a negative float (e.g. -18.5), or None if unavailable.
    """
    try:
        from investimentos.tools.risk import compute_max_drawdown

        yf_client = YFinanceClient()
        total_weight = sum(allocation_pct.values())
        if total_weight == 0:
            return None

        # Collect daily close prices per ticker
        ticker_series: dict[str, dict[str, Decimal]] = {}
        for ticker in list(allocation_pct.keys())[:12]:  # cap at 12 to avoid slow startup
            try:
                hist = yf_client.get_historical(f"{ticker}.SA", period="1y", interval="1d")
                if hist:
                    ticker_series[ticker] = {row["date"]: row["close"] for row in hist}
            except Exception:
                pass

        if not ticker_series:
            return None

        # Align dates across all tickers that have history
        all_dates = sorted(
            set.intersection(*[set(v.keys()) for v in ticker_series.values()])
        )
        if len(all_dates) < 20:
            return None

        # Build weighted portfolio value series (base = 100 at first date)
        first_prices = {t: series[all_dates[0]] for t, series in ticker_series.items()}
        portfolio_values: list[Decimal] = []
        for d in all_dates:
            port_val = Decimal("0")
            for ticker, series in ticker_series.items():
                weight = Decimal(str(allocation_pct.get(ticker, 0))) / Decimal("100")
                if first_prices[ticker] > 0:
                    relative = series[d] / first_prices[ticker]
                    port_val += weight * relative * Decimal("100")
            portfolio_values.append(port_val)

        dd = compute_max_drawdown(portfolio_values)
        return -float(dd)  # return as negative number (convention: -18.5 means 18.5% drawdown)
    except Exception:
        return None
