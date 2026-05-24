import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from investimentos.domain.db import Base
from investimentos.domain.models import EquityPositionSnapshot, FixedIncomePosition, PortfolioSnapshot
from investimentos.repository.portfolio_snapshot_repo import PortfolioSnapshotRepository


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_snap(account_id="acc-1", snap_date=date(2026, 5, 22)):
    return PortfolioSnapshot(
        account_id=account_id,
        snapshot_date=snap_date,
        source_file="extrato.pdf",
        equity_positions=[
            EquityPositionSnapshot(ticker="ITUB4", quantity=Decimal("12"), avg_cost_hint=Decimal("39.38")),
        ],
        fixed_income_positions=[
            FixedIncomePosition(
                name="CDB Fibra",
                issuer="Banco Fibra",
                invested_amount=Decimal("5000"),
                rate_description="113% CDI",
                current_value=Decimal("5100"),
            ),
        ],
    )


def test_save_and_get_latest(session):
    repo = PortfolioSnapshotRepository(session)
    snap = _make_snap()
    repo.save(snap)
    latest = repo.get_latest("acc-1")
    assert latest is not None
    assert latest.snapshot_date == date(2026, 5, 22)
    assert len(latest.equity_positions) == 1
    assert latest.equity_positions[0].ticker == "ITUB4"
    assert latest.equity_positions[0].avg_cost_hint == Decimal("39.38")


def test_get_latest_returns_newest_by_date(session):
    repo = PortfolioSnapshotRepository(session)
    repo.save(_make_snap(snap_date=date(2026, 4, 30)))
    repo.save(_make_snap(snap_date=date(2026, 5, 22)))
    latest = repo.get_latest("acc-1")
    assert latest.snapshot_date == date(2026, 5, 22)


def test_get_latest_none_when_empty(session):
    repo = PortfolioSnapshotRepository(session)
    assert repo.get_latest("acc-1") is None


def test_get_latest_scoped_to_account(session):
    repo = PortfolioSnapshotRepository(session)
    repo.save(_make_snap(account_id="acc-1"))
    assert repo.get_latest("acc-2") is None


def test_get_equity_position_found(session):
    repo = PortfolioSnapshotRepository(session)
    repo.save(_make_snap())
    pos = repo.get_equity_position("acc-1", "ITUB4")
    assert pos is not None
    assert pos.quantity == Decimal("12")


def test_get_equity_position_case_insensitive(session):
    repo = PortfolioSnapshotRepository(session)
    repo.save(_make_snap())
    pos = repo.get_equity_position("acc-1", "itub4")
    assert pos is not None


def test_get_equity_position_not_found(session):
    repo = PortfolioSnapshotRepository(session)
    repo.save(_make_snap())
    assert repo.get_equity_position("acc-1", "PETR4") is None


def test_list_snapshots_ordered_by_date(session):
    repo = PortfolioSnapshotRepository(session)
    repo.save(_make_snap(snap_date=date(2026, 5, 22)))
    repo.save(_make_snap(snap_date=date(2026, 4, 30)))
    snaps = repo.list_snapshots("acc-1")
    assert len(snaps) == 2
    assert snaps[0].snapshot_date < snaps[1].snapshot_date


def test_fixed_income_round_trips(session):
    repo = PortfolioSnapshotRepository(session)
    repo.save(_make_snap())
    latest = repo.get_latest("acc-1")
    fi = latest.fixed_income_positions[0]
    assert fi.name == "CDB Fibra"
    assert fi.issuer == "Banco Fibra"
    assert fi.rate_description == "113% CDI"
    assert fi.current_value == Decimal("5100")
