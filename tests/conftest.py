import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from investimentos.domain.db import Base

@pytest.fixture(scope="function")
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)

@pytest.fixture(scope="function")
def db_session(engine):
    session = Session(engine)
    yield session
    session.close()
