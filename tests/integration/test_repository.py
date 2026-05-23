import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from investimentos.domain.db import Base, engine_from_url, AccountORM, AssetORM, TransactionORM

@pytest.fixture
def engine():
    eng = engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)

def test_tables_created(engine):
    with engine.connect() as conn:
        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        table_names = [t[0] for t in tables]
    assert "accounts" in table_names
    assert "assets" in table_names
    assert "transactions" in table_names

def test_insert_account(engine):
    with Session(engine) as session:
        acc = AccountORM(id="acc-1", name="Clear", account_type="ctvm", custodian="Clear")
        session.add(acc)
        session.commit()
        found = session.get(AccountORM, "acc-1")
    assert found.name == "Clear"


from investimentos.repository.account import AccountRepository
from investimentos.domain.models import Account, AccountType

def test_account_repository_save_and_get(engine):
    repo = AccountRepository(Session(engine))
    acc = Account(id="acc-2", name="XP", account_type=AccountType.CTVM, custodian="XP")
    repo.save(acc)
    found = repo.get_by_id("acc-2")
    assert found is not None
    assert found.name == "XP"

def test_account_repository_list_all(engine):
    session = Session(engine)
    repo = AccountRepository(session)
    repo.save(Account(id="a1", name="Clear", account_type=AccountType.CTVM, custodian="Clear"))
    repo.save(Account(id="a2", name="XP", account_type=AccountType.CTVM, custodian="XP"))
    accounts = repo.list_all()
    assert len(accounts) == 2


from decimal import Decimal
from datetime import date
from investimentos.repository.transaction import TransactionRepository
from investimentos.repository.holding import HoldingComputer
from investimentos.domain.models import Transaction, TransactionType

def test_transaction_save_and_list(engine):
    session = Session(engine)
    from investimentos.repository.account import AccountRepository
    AccountRepository(session).save(
        Account(id="acc-t", name="Test", account_type=AccountType.CTVM, custodian="Test")
    )
    repo = TransactionRepository(session)
    t = Transaction(
        id="tx-1", account_id="acc-t", ticker="PETR4",
        transaction_type=TransactionType.COMPRA,
        quantity=Decimal("100"), unit_price=Decimal("30.00"),
        date=date(2024, 1, 10),
    )
    repo.save(t)
    txns = repo.list_by_ticker("PETR4")
    assert len(txns) == 1
    assert txns[0].quantity == Decimal("100")

def test_holding_computer_average_cost(engine):
    session = Session(engine)
    from investimentos.repository.account import AccountRepository
    AccountRepository(session).save(
        Account(id="acc-h", name="Test", account_type=AccountType.CTVM, custodian="Test")
    )
    repo = TransactionRepository(session)
    repo.save(Transaction(
        id="tx-h1", account_id="acc-h", ticker="ITUB4",
        transaction_type=TransactionType.COMPRA,
        quantity=Decimal("100"), unit_price=Decimal("25.00"),
        date=date(2024, 1, 1),
    ))
    repo.save(Transaction(
        id="tx-h2", account_id="acc-h", ticker="ITUB4",
        transaction_type=TransactionType.COMPRA,
        quantity=Decimal("100"), unit_price=Decimal("27.00"),
        date=date(2024, 2, 1),
    ))
    computer = HoldingComputer(repo)
    holdings = computer.compute("ITUB4")
    assert len(holdings) == 1
    assert holdings[0].quantity == Decimal("200")
    assert holdings[0].average_cost == Decimal("26.0000")
