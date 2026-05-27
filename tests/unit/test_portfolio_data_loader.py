"""Unit tests for portfolio_data_loader_node."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from investimentos.domain.db import Base, AccountORM, TransactionORM
from investimentos.domain.models import EquityPositionSnapshot, PortfolioSnapshot
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


@patch("investimentos.agents.portfolio_data_loader._fetch_prices", return_value={})
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_empty_db_returns_empty_summary(mock_engine, mock_prices, db_engine):
    mock_engine.return_value = db_engine
    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node

    out = portfolio_data_loader_node(AgentState(user_query="x"))
    summary = out["portfolio_summary"]
    assert summary["source"] == "empty"
    assert summary["allocation_pct"] == {}
    assert summary["hhi"] is None


@patch("investimentos.agents.portfolio_data_loader._fetch_prices", return_value={"ITUB4": Decimal("40.00")})
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_reads_transactions(mock_engine, mock_prices, db_engine):
    mock_engine.return_value = db_engine
    with Session(db_engine) as s:
        _add_account(s)
        _add_transaction(s, "ITUB4", 10, 39.38)
        _add_transaction(s, "PETR4", 5, 35.00)

    # no market price for PETR4, falls back to avg_cost
    mock_prices.return_value = {"ITUB4": Decimal("40.00"), "PETR4": Decimal("35.00")}

    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
    out = portfolio_data_loader_node(AgentState(user_query="x"))
    summary = out["portfolio_summary"]
    assert summary["source"] == "transactions"
    assert "ITUB4" in summary["allocation_pct"]
    assert "PETR4" in summary["allocation_pct"]
    assert summary["hhi"] is not None
    assert 0 < summary["hhi"] <= 1


@patch("investimentos.agents.portfolio_data_loader._fetch_prices", return_value={})
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_fallback_to_snapshot(mock_engine, mock_prices, db_engine):
    mock_engine.return_value = db_engine
    # No transactions, but a snapshot exists
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
    assert summary["allocation_pct"]["WEGE3"] == pytest.approx(100.0)


@patch("investimentos.agents.portfolio_data_loader._fetch_prices", return_value={"ITUB4": Decimal("40.00")})
@patch("investimentos.agents.portfolio_data_loader.engine_from_url")
def test_loader_hhi_single_asset_is_one(mock_engine, mock_prices, db_engine):
    mock_engine.return_value = db_engine
    with Session(db_engine) as s:
        _add_account(s)
        _add_transaction(s, "ITUB4", 10, 39.38)

    from investimentos.agents.portfolio_data_loader import portfolio_data_loader_node
    out = portfolio_data_loader_node(AgentState(user_query="x"))
    assert out["portfolio_summary"]["hhi"] == pytest.approx(1.0, abs=0.001)
