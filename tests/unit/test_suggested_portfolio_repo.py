from decimal import Decimal

from investimentos.domain.models import (
    AssetClass,
    SuggestedAssetAllocation,
    SuggestedClassAllocation,
    SuggestedPortfolio,
    SuggestedPortfolioStatus,
)
from investimentos.repository.suggested_portfolio_repo import SuggestedPortfolioRepository


def _sample():
    return SuggestedPortfolio(
        name="X",
        source_file="x.pdf",
        class_allocations=[
            SuggestedClassAllocation(asset_class=AssetClass.ACAO, target_pct=Decimal("100"))
        ],
        asset_allocations=[
            SuggestedAssetAllocation(ticker="ITUB4", target_pct=Decimal("5"), thesis="ok")
        ],
    )


def test_save_and_load(db_session):
    repo = SuggestedPortfolioRepository(db_session)
    sp = _sample()
    repo.save(sp)
    loaded = repo.get(sp.id)
    assert loaded.name == "X"
    assert loaded.asset_allocations[0].ticker == "ITUB4"


def test_get_thesis_for(db_session):
    repo = SuggestedPortfolioRepository(db_session)
    sp = _sample()
    repo.save(sp)
    repo.activate(sp.id)
    assert "ok" in repo.get_thesis_for("ITUB4")


def test_get_thesis_for_returns_none_when_no_active(db_session):
    repo = SuggestedPortfolioRepository(db_session)
    sp = _sample()
    repo.save(sp)
    assert repo.get_thesis_for("ITUB4") is None


def test_activate_archives_previous(db_session):
    repo = SuggestedPortfolioRepository(db_session)
    a = _sample()
    b = _sample()
    repo.save(a)
    repo.activate(a.id)
    repo.save(b)
    repo.activate(b.id)
    assert repo.get(a.id).status == SuggestedPortfolioStatus.ARCHIVED
    assert repo.get(b.id).status == SuggestedPortfolioStatus.ACTIVE
