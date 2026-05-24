from datetime import datetime, date
from decimal import Decimal
import pytest
from investimentos.domain.models import (
    Account, AccountType, Asset, AssetClass, TaxClass
)

def test_account_creation():
    acc = Account(
        id="acc-1",
        name="Clear Corretora",
        account_type=AccountType.CTVM,
        custodian="Clear",
    )
    assert acc.name == "Clear Corretora"
    assert acc.account_type == AccountType.CTVM

def test_asset_creation():
    asset = Asset(
        ticker="PETR4",
        name="Petrobras PN",
        asset_class=AssetClass.ACAO,
        tax_class=TaxClass.RENDA_VARIAVEL,
    )
    assert asset.ticker == "PETR4"
    assert asset.asset_class == AssetClass.ACAO

def test_asset_ticker_uppercase():
    asset = Asset(
        ticker="petr4",
        name="Petrobras",
        asset_class=AssetClass.ACAO,
        tax_class=TaxClass.RENDA_VARIAVEL,
    )
    assert asset.ticker == "PETR4"

def test_account_type_enum_values():
    assert AccountType.CTVM.value == "ctvm"
    assert AccountType.BANCO.value == "banco"
    assert AccountType.FINTECH.value == "fintech"


# Task 5: Transaction and Holding
from investimentos.domain.models import Transaction, TransactionType, Holding

def test_transaction_compra():
    t = Transaction(
        id="t-1",
        account_id="acc-1",
        ticker="PETR4",
        transaction_type=TransactionType.COMPRA,
        quantity=Decimal("100"),
        unit_price=Decimal("35.50"),
        date=date(2024, 1, 15),
    )
    assert t.gross_value == Decimal("3550.00")
    assert t.net_value == Decimal("3550.00")

def test_transaction_with_fees():
    t = Transaction(
        id="t-2",
        account_id="acc-1",
        ticker="PETR4",
        transaction_type=TransactionType.COMPRA,
        quantity=Decimal("100"),
        unit_price=Decimal("35.50"),
        date=date(2024, 1, 15),
        fees=Decimal("4.50"),
    )
    assert t.gross_value == Decimal("3550.00")
    assert t.net_value == Decimal("3554.50")

def test_holding_creation():
    h = Holding(
        ticker="PETR4",
        account_id="acc-1",
        quantity=Decimal("100"),
        average_cost=Decimal("35.50"),
        current_price=Decimal("40.00"),
    )
    assert h.market_value == Decimal("4000.00")
    assert h.unrealized_pnl == Decimal("450.00")
    assert h.unrealized_pnl_pct == pytest.approx(Decimal("12.676"), abs=Decimal("0.001"))


# Task 6: InvestorProfile, PortfolioObjective, TaxEvent
from investimentos.domain.models import (
    InvestorProfile, RiskProfile, PortfolioObjective, AllocationTarget, TaxEvent
)

def test_investor_profile_versioned():
    p = InvestorProfile(
        id="ip-1",
        risk_profile=RiskProfile.MODERADO,
        horizon_years=10,
        valid_from=date(2024, 1, 1),
    )
    assert p.valid_to is None
    assert p.risk_profile == RiskProfile.MODERADO

def test_portfolio_objective_allocations_sum_to_100():
    obj = PortfolioObjective(
        id="po-1",
        name="Crescimento",
        allocations=[
            AllocationTarget(asset_class=AssetClass.ACAO, target_pct=Decimal("60")),
            AllocationTarget(asset_class=AssetClass.RENDA_FIXA, target_pct=Decimal("30")),
            AllocationTarget(asset_class=AssetClass.FII, target_pct=Decimal("10")),
        ],
        valid_from=date(2024, 1, 1),
    )
    total = sum(a.target_pct for a in obj.allocations)
    assert total == Decimal("100")

from investimentos.domain.models import (
    SuggestedPortfolio, SuggestedAssetAllocation, SuggestedClassAllocation,
    SuggestedPortfolioStatus,
)

def test_suggested_portfolio_minimal():
    sp = SuggestedPortfolio(
        name="Carteira XP",
        source_file="x.pdf",
        class_allocations=[SuggestedClassAllocation(asset_class=AssetClass.ACAO, target_pct=Decimal("50"))],
        asset_allocations=[SuggestedAssetAllocation(ticker="itub4", target_pct=Decimal("5"), thesis="ok")],
    )
    assert sp.status == SuggestedPortfolioStatus.DRAFT
    assert sp.asset_allocations[0].ticker == "ITUB4"
    assert isinstance(sp.imported_at, datetime)

def test_suggested_portfolio_allocations_optional_zero():
    sp = SuggestedPortfolio(name="x", source_file="x")
    assert sp.class_allocations == []
    assert sp.asset_allocations == []


def test_portfolio_objective_allocations_not_100_raises():
    with pytest.raises(ValueError, match="sum to 100"):
        PortfolioObjective(
            id="po-2",
            name="Errado",
            allocations=[
                AllocationTarget(asset_class=AssetClass.ACAO, target_pct=Decimal("60")),
            ],
            valid_from=date(2024, 1, 1),
        )
