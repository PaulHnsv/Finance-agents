from datetime import datetime
from sqlalchemy import (
    Column, String, Numeric, Integer, Boolean, DateTime, Date,
    ForeignKey, Text, JSON, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class AccountORM(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    custodian = Column(String, nullable=False)
    brokerage_fee_pct = Column(Numeric(10, 4), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    transactions = relationship("TransactionORM", back_populates="account")


class AssetORM(Base):
    __tablename__ = "assets"
    ticker = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    asset_class = Column(String, nullable=False)
    tax_class = Column(String, nullable=False)
    isin = Column(String, nullable=True)
    cnpj = Column(String, nullable=True)


class TransactionORM(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    ticker = Column(String, nullable=False)
    transaction_type = Column(String, nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    unit_price = Column(Numeric(20, 8), nullable=False)
    date = Column(Date, nullable=False)
    fees = Column(Numeric(10, 4), default=0)
    irrf = Column(Numeric(10, 4), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    account = relationship("AccountORM", back_populates="transactions")


class InvestorProfileORM(Base):
    __tablename__ = "investor_profiles"
    id = Column(String, primary_key=True)
    risk_profile = Column(String, nullable=False)
    horizon_years = Column(Integer, nullable=False)
    monthly_income = Column(Numeric(15, 2), nullable=True)
    monthly_expenses = Column(Numeric(15, 2), nullable=True)
    questionnaire_answers = Column(JSON, default=dict)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PortfolioObjectiveORM(Base):
    __tablename__ = "portfolio_objectives"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    allocations_json = Column(JSON, nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TaxEventORM(Base):
    __tablename__ = "tax_events"
    id = Column(String, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    tax_due = Column(Numeric(15, 2), default=0)
    tax_paid = Column(Numeric(15, 2), default=0)
    accumulated_loss = Column(Numeric(15, 2), default=0)
    darf_code = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def engine_from_url(url: str):
    return create_engine(url, echo=False)
