"""Unit tests for portfolio_data_loader_node."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from investimentos.domain.db import Base, AccountORM, TransactionORM
from investimentos.domain.models import EquityPositionSnapshot, FixedIncomePosition, PortfolioSnapshot
from investimentos.agents.state import AgentState


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _add_account(session: Session):
    session.merge(AccountORM(id="acc-1", name="Test", account_type="ctvm", custodian="X"))
    session.commit()


def _add_transaction(session: Session, ticker: str, qty: float, price: float, txn_date=date(2026, 5, 1)):
    from investimentos.domain.models import new_id
    session.merge(TransactionORM(
        id=new_id(),
        account_id="acc-1",
        ticker=ticker,
        transaction_type="compra",
        quantity=Decimal(str(qty)),
        unit_price=Decimal(str(price)),
        date=txn_date,
        fees=Decimal("0"),
    ))
    session.commit()


def _quote(price: float, industry: str = "", quote_type: str = "") -> dict:
    return {"price": Decimal(str(price)), "industry": industry, "quote_type": quote_type}


@patch("investimentos.agents.portfolio_data_loader._fetch_quotes", return_value={})
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_empty_db_returns_empty_summary(mock_engine, mock_quotes, db_engine):
    mock_engine.return_value = db_engine
    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node

    out = portfolio_data_loader_node(AgentState(user_query="x"))
    summary = out["portfolio_summary"]
    assert summary["source"] == "empty"
    assert summary["allocation_pct"] == {}
    assert summary["hhi"] is None


@patch("investimentos.agents.portfolio_data_loader._fetch_quotes")
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_reads_transactions(mock_engine, mock_quotes, db_engine):
    mock_engine.return_value = db_engine
    mock_quotes.return_value = {
        "ITUB4": _quote(40.0),
        "PETR4": _quote(35.0),
    }

    with Session(db_engine) as s:
        _add_account(s)
        _add_transaction(s, "ITUB4", 10, 39.38)
        _add_transaction(s, "PETR4", 5, 35.00)

    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
    out = portfolio_data_loader_node(AgentState(user_query="x"))
    summary = out["portfolio_summary"]
    assert summary["source"] == "transactions"
    assert "ITUB4" in summary["allocation_pct"]
    assert "PETR4" in summary["allocation_pct"]
    assert summary["hhi"] is not None
    assert 0 < summary["hhi"] <= 1


@patch("investimentos.agents.portfolio_data_loader._fetch_quotes", return_value={})
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_fallback_to_snapshot(mock_engine, mock_quotes, db_engine):
    mock_engine.return_value = db_engine
    snap = PortfolioSnapshot(
        account_id="acc-1",
        snapshot_date=date(2026, 5, 22),
        source_file="extrato.pdf",
        equity_positions=[
            EquityPositionSnapshot(ticker="WEGE3", quantity=Decimal("20"), avg_cost_hint=Decimal("50.00")),
        ],
    )
    from investimentos.repository.portfolio_snapshot_repo import PortfolioSnapshotRepository
    with Session(db_engine) as s:
        PortfolioSnapshotRepository(s).save(snap)

    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
    out = portfolio_data_loader_node(AgentState(user_query="x", account_id="acc-1"))
    summary = out["portfolio_summary"]
    assert summary["source"] == "snapshot"
    assert "WEGE3" in summary["allocation_pct"]


@patch("investimentos.agents.portfolio_data_loader._fetch_quotes")
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_hhi_single_asset_is_one(mock_engine, mock_quotes, db_engine):
    mock_engine.return_value = db_engine
    mock_quotes.return_value = {"ITUB4": _quote(40.0)}

    with Session(db_engine) as s:
        _add_account(s)
        _add_transaction(s, "ITUB4", 10, 39.38)

    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
    out = portfolio_data_loader_node(AgentState(user_query="x"))
    assert out["portfolio_summary"]["hhi"] == pytest.approx(1.0, abs=0.001)


@patch("investimentos.agents.portfolio_data_loader._fetch_quotes", return_value={})
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_includes_fi_from_snapshot(mock_engine, mock_quotes, db_engine):
    """Fixed income from snapshot appears in allocation_pct as 'renda_fixa'."""
    mock_engine.return_value = db_engine
    snap = PortfolioSnapshot(
        account_id="acc-1",
        snapshot_date=date(2026, 5, 22),
        source_file="extrato.pdf",
        equity_positions=[
            EquityPositionSnapshot(ticker="ITUB4", quantity=Decimal("10"), avg_cost_hint=Decimal("40.00")),
        ],
        fixed_income_positions=[
            FixedIncomePosition(name="CDB X", invested_amount=Decimal("1000"), current_value=Decimal("1000")),
        ],
    )
    from investimentos.repository.portfolio_snapshot_repo import PortfolioSnapshotRepository
    with Session(db_engine) as s:
        PortfolioSnapshotRepository(s).save(snap)

    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
    out = portfolio_data_loader_node(AgentState(user_query="x", account_id="acc-1"))
    summary = out["portfolio_summary"]
    assert "renda_fixa" in summary["allocation_pct"]
    assert summary["allocation_pct"]["renda_fixa"] > 0


def test_compute_portfolio_max_drawdown_with_mock():
    from investimentos.agents.portfolio_data_loader import _compute_portfolio_max_drawdown

    dates = [f"2026-{str(i // 30 + 3).zfill(2)}-{str(i % 30 + 1).zfill(2)}" for i in range(60)]
    prices = [Decimal(str(100 - i)) if i < 30 else Decimal(str(70 + (i - 30))) for i in range(60)]
    hist = [{"date": d, "close": p, "volume": 1000} for d, p in zip(dates, prices)]

    mock_yf = MagicMock()
    mock_yf.get_historical.return_value = hist

    with patch("investimentos.agents.portfolio_data_loader.YFinanceClient", return_value=mock_yf):
        result = _compute_portfolio_max_drawdown(
            [{"ticker": "ITUB4", "qty": Decimal("10"), "avg_cost": Decimal("100"), "current_price": Decimal("100")}],
            {"ITUB4": 100.0},
        )

    assert result is not None
    assert result < 0
    assert result == pytest.approx(-30.0, abs=1.0)


def test_compute_portfolio_max_drawdown_returns_none_on_error():
    from investimentos.agents.portfolio_data_loader import _compute_portfolio_max_drawdown
    with patch("investimentos.agents.portfolio_data_loader.YFinanceClient", side_effect=Exception("no network")):
        result = _compute_portfolio_max_drawdown(
            [{"ticker": "ITUB4", "qty": Decimal("10"), "avg_cost": Decimal("100"), "current_price": Decimal("100")}],
            {"ITUB4": 100.0},
        )
    assert result is None


def test_loader_exposes_holdings_detail_with_catalog_classification(db_engine):
    from investimentos.domain.db import AssetORM
    with Session(db_engine) as s:
        _add_account(s)
        _add_transaction(s, "ALUP11", 10, 30.0)
        s.add(AssetORM(
            ticker="ALUP11", name="Alupar Investimento",
            asset_class="acao", tax_class="renda_variavel",
        ))
        s.commit()

    with patch(
        "investimentos.agents.portfolio_data_loader._fetch_quotes",
        return_value={"ALUP11": {"price": Decimal("31.0"), "industry": "", "quote_type": ""}},
    ), patch(
        "investimentos.agents.portfolio_data_loader.engine_from_url",
        return_value=db_engine,
    ):
        from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
        out = portfolio_data_loader_node(AgentState(user_query="x"))

    summary = out["portfolio_summary"]
    assert "holdings_detail" in summary
    details = summary["holdings_detail"]
    assert len(details) == 1
    assert details[0]["ticker"] == "ALUP11"
    assert details[0]["asset_class"] == "acao"
    assert details[0]["display_name"] == "Alupar Investimento"
