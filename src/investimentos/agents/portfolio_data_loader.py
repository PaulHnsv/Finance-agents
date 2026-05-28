"""Portfolio Data Loader — reads holdings from DB; uses AssetCatalogService for classification."""
from decimal import Decimal
from typing import Optional

from investimentos.agents.state import AgentState
from investimentos.config import get_settings
from investimentos.domain.asset_catalog import AssetCatalogService
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
        fi_total = _load_fi_total_from_snapshot(session, account_id)

        if not holdings and fi_total == 0:
            return {"portfolio_summary": {
                "source": "empty", "allocation_pct": {}, "hhi": None, "holdings_detail": [],
            }}

        quotes = _fetch_quotes([h["ticker"] for h in holdings])
        for h in holdings:
            h["current_price"] = quotes.get(h["ticker"], {}).get("price", h["avg_cost"])

        equity_value = sum((h["qty"] * h["current_price"] for h in holdings), Decimal("0"))
        total_value = equity_value + fi_total
        if total_value == 0:
            return {"portfolio_summary": {
                "source": source, "allocation_pct": {}, "hhi": None, "holdings_detail": [],
            }}

        catalog = AssetCatalogService(session, yf_client=YFinanceClient())
        classifications = {h["ticker"]: catalog.classify(h["ticker"]) for h in holdings}

        allocation_pct: dict[str, float] = {
            h["ticker"]: float(((h["qty"] * h["current_price"]) / total_value * 100).quantize(Decimal("0.01")))
            for h in holdings
        }
        if fi_total > 0:
            allocation_pct["renda_fixa"] = float((fi_total / total_value * 100).quantize(Decimal("0.01")))

        equity_pct = {k: v for k, v in allocation_pct.items() if k != "renda_fixa"}
        weights = [Decimal(str(v)) / Decimal("100") for v in equity_pct.values()]
        hhi = float(sum(w ** 2 for w in weights).quantize(Decimal("0.0001"))) if weights else None

        drift = _compute_drift_with_catalog(holdings, classifications, total_value, engine, fi_total)

        holdings_detail = [
            {
                "ticker": h["ticker"],
                "display_name": classifications[h["ticker"]].display_name,
                "asset_class": classifications[h["ticker"]].asset_class.value,
                "allocation_pct": allocation_pct[h["ticker"]],
            }
            for h in holdings
        ]

        return {
            "portfolio_summary": {
                "source": source,
                "allocation_pct": allocation_pct,
                "hhi": hhi,
                "drift": drift,
                "holdings_detail": holdings_detail,
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
    from investimentos.repository.portfolio_snapshot_repo import PortfolioSnapshotRepository

    repo = PortfolioSnapshotRepository(session)
    snap = repo.get_latest(account_id or "")
    if snap is None:
        return Decimal("0")
    return sum((fi.current_value for fi in snap.fixed_income_positions), Decimal("0"))


def _fetch_quotes(tickers: list[str]) -> dict[str, dict]:
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


def _compute_drift_with_catalog(
    holdings: list[dict],
    classifications: dict,
    total_value: Decimal,
    engine,
    fi_total: Decimal,
) -> dict:
    from investimentos.tools.allocation_drift import compute_drift
    from investimentos.domain.models import AssetClass
    from investimentos.domain.db import SuggestedPortfolioORM

    class_values: dict[str, Decimal] = {}
    for h in holdings:
        cls = classifications[h["ticker"]].asset_class.value
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
    try:
        from investimentos.tools.risk import compute_max_drawdown

        yf_client = YFinanceClient()
        total_weight = sum(allocation_pct.values())
        if total_weight == 0:
            return None

        ticker_series: dict[str, dict[str, Decimal]] = {}
        for ticker in list(allocation_pct.keys())[:12]:
            try:
                hist = yf_client.get_historical(f"{ticker}.SA", period="1y", interval="1d")
                if hist:
                    ticker_series[ticker] = {row["date"]: row["close"] for row in hist}
            except Exception:
                pass

        if not ticker_series:
            return None

        all_dates = sorted(
            set.intersection(*[set(v.keys()) for v in ticker_series.values()])
        )
        if len(all_dates) < 20:
            return None

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
        return -float(dd)
    except Exception:
        return None
