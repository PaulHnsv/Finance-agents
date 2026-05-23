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
