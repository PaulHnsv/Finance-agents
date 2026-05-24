from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, field_validator, Field


def new_id() -> str:
    return str(uuid.uuid4())


class AccountType(str, Enum):
    CTVM = "ctvm"
    BANCO = "banco"
    FINTECH = "fintech"
    PREVIDENCIA = "previdencia"


class AssetClass(str, Enum):
    ACAO = "acao"
    FII = "fii"
    ETF = "etf"
    RENDA_FIXA = "renda_fixa"
    TESOURO = "tesouro"
    FUNDO = "fundo"
    BDR = "bdr"
    CAIXA = "caixa"


class TaxClass(str, Enum):
    RENDA_VARIAVEL = "renda_variavel"
    FII = "fii"
    DAY_TRADE = "day_trade"
    RENDA_FIXA = "renda_fixa"
    TESOURO_DIRETO = "tesouro_direto"
    ISENTO = "isento"


class Account(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    account_type: AccountType
    custodian: str
    brokerage_fee_pct: Decimal = Decimal("0")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Asset(BaseModel):
    ticker: str
    name: str
    asset_class: AssetClass
    tax_class: TaxClass
    isin: Optional[str] = None
    cnpj: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()


class TransactionType(str, Enum):
    COMPRA = "compra"
    VENDA = "venda"
    DIVIDENDO = "dividendo"
    JCP = "jcp"
    TAXA = "taxa"
    IRRF = "irrf"
    BONIFICACAO = "bonificacao"
    DESDOBRAMENTO = "desdobramento"
    GRUPAMENTO = "grupamento"


class Transaction(BaseModel):
    id: str = Field(default_factory=new_id)
    account_id: str
    ticker: str
    transaction_type: TransactionType
    quantity: Decimal
    unit_price: Decimal
    date: date
    fees: Decimal = Decimal("0")
    irrf: Decimal = Decimal("0")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def gross_value(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    @property
    def net_value(self) -> Decimal:
        return self.gross_value + self.fees


class Holding(BaseModel):
    """Derived, never stored as fact — computed from transactions."""
    ticker: str
    account_id: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal

    @property
    def market_value(self) -> Decimal:
        return (self.quantity * self.current_price).quantize(Decimal("0.01"))

    @property
    def cost_basis(self) -> Decimal:
        return (self.quantity * self.average_cost).quantize(Decimal("0.01"))

    @property
    def unrealized_pnl(self) -> Decimal:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> Decimal:
        if self.cost_basis == 0:
            return Decimal("0")
        return ((self.unrealized_pnl / self.cost_basis) * 100).quantize(Decimal("0.001"))


class RiskProfile(str, Enum):
    CONSERVADOR = "conservador"
    MODERADO = "moderado"
    ARROJADO = "arrojado"
    AGRESSIVO = "agressivo"


class AllocationTarget(BaseModel):
    asset_class: AssetClass
    target_pct: Decimal


class InvestorProfile(BaseModel):
    id: str = Field(default_factory=new_id)
    risk_profile: RiskProfile
    horizon_years: int
    monthly_income: Optional[Decimal] = None
    monthly_expenses: Optional[Decimal] = None
    questionnaire_answers: dict = Field(default_factory=dict)
    valid_from: date
    valid_to: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PortfolioObjective(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: Optional[str] = None
    allocations: list[AllocationTarget]
    valid_from: date
    valid_to: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("allocations")
    @classmethod
    def allocations_must_sum_to_100(cls, v: list[AllocationTarget]) -> list[AllocationTarget]:
        total = sum(a.target_pct for a in v)
        if abs(total - Decimal("100")) > Decimal("0.01"):
            raise ValueError(f"Allocations must sum to 100, got {total}")
        return v


class SuggestedPortfolioStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SuggestedClassAllocation(BaseModel):
    asset_class: AssetClass
    target_pct: Decimal


class SuggestedAssetAllocation(BaseModel):
    ticker: str
    target_pct: Decimal
    thesis: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()


class SuggestedPortfolio(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    source_file: str
    risk_profile_hint: Optional[RiskProfile] = None
    class_allocations: list[SuggestedClassAllocation] = Field(default_factory=list)
    asset_allocations: list[SuggestedAssetAllocation] = Field(default_factory=list)
    status: SuggestedPortfolioStatus = SuggestedPortfolioStatus.DRAFT
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None


class TaxEvent(BaseModel):
    id: str = Field(default_factory=new_id)
    year: int
    month: int
    tax_due: Decimal = Decimal("0")
    tax_paid: Decimal = Decimal("0")
    accumulated_loss: Decimal = Decimal("0")
    darf_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EquityPositionSnapshot(BaseModel):
    """Equity position from an account statement (stored, not computed)."""
    ticker: str
    quantity: Decimal
    avg_cost_hint: Optional[Decimal] = None

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()


class FixedIncomePosition(BaseModel):
    """Fixed income holding without exchange ticker (CDB, LCI, LCA, etc.)."""
    name: str
    issuer: Optional[str] = None
    maturity_date: Optional[date] = None
    invested_amount: Decimal
    rate_description: Optional[str] = None
    current_value: Decimal


class PortfolioSnapshot(BaseModel):
    """Snapshot of holdings at a point in time, imported from an account statement."""
    id: str = Field(default_factory=new_id)
    account_id: str
    snapshot_date: date
    source_file: str
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    equity_positions: list[EquityPositionSnapshot] = Field(default_factory=list)
    fixed_income_positions: list[FixedIncomePosition] = Field(default_factory=list)
