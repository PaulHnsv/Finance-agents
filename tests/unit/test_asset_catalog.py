from investimentos.domain.asset_catalog import AssetClassification
from investimentos.domain.models import AssetClass


def test_asset_classification_required_fields():
    c = AssetClassification(
        ticker="ITUB4",
        asset_class=AssetClass.ACAO,
        display_name="Itaú Unibanco PN",
        source="catalog",
    )
    assert c.ticker == "ITUB4"
    assert c.asset_class == AssetClass.ACAO
    assert c.sector is None
    assert c.source == "catalog"

from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from investimentos.domain.asset_catalog import AssetCatalogService
from investimentos.domain.db import Base, AssetORM


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_classify_from_catalog(session):
    session.add(AssetORM(
        ticker="ITUB4", name="Itau PN", asset_class="acao",
        tax_class="renda_variavel",
    ))
    session.commit()
    svc = AssetCatalogService(session, yf_client=MagicMock())
    c = svc.classify("itub4")
    assert c.asset_class == AssetClass.ACAO
    assert c.display_name == "Itau PN"
    assert c.source == "catalog"


def test_classify_falls_back_to_yfinance_reit_industry(session):
    yf = MagicMock()
    yf.get_quote.return_value = {
        "ticker": "HGLG11.SA", "name": "CSHG Logistica FII",
        "industry": "REIT - Diversified", "quote_type": "ETF",
    }
    svc = AssetCatalogService(session, yf_client=yf)
    c = svc.classify("HGLG11")
    assert c.asset_class == AssetClass.FII
    assert c.source == "yfinance"


def test_classify_falls_back_to_yfinance_equity(session):
    yf = MagicMock()
    yf.get_quote.return_value = {
        "ticker": "ALUP11.SA", "name": "Alupar Investimento",
        "industry": "Utilities - Regulated Electric", "quote_type": "EQUITY",
    }
    svc = AssetCatalogService(session, yf_client=yf)
    c = svc.classify("ALUP11")
    assert c.asset_class == AssetClass.ACAO
    assert c.source == "yfinance"


def test_classify_etf_prefix_is_etf(session):
    yf = MagicMock()
    yf.get_quote.side_effect = Exception("offline")
    svc = AssetCatalogService(session, yf_client=yf)
    c = svc.classify("BOVA11")
    assert c.asset_class == AssetClass.ETF
    assert c.source == "heuristic"


def test_classify_heuristic_acao_for_3_4_suffix(session):
    yf = MagicMock()
    yf.get_quote.side_effect = Exception("offline")
    svc = AssetCatalogService(session, yf_client=yf)
    assert svc.classify("PETR4").asset_class == AssetClass.ACAO
    assert svc.classify("VALE3").asset_class == AssetClass.ACAO


def test_classify_caches_results(session):
    yf = MagicMock()
    yf.get_quote.return_value = {
        "ticker": "WEGE3.SA", "name": "WEG",
        "industry": "Industrials", "quote_type": "EQUITY",
    }
    svc = AssetCatalogService(session, yf_client=yf)
    svc.classify("WEGE3")
    svc.classify("WEGE3")
    svc.classify("WEGE3")
    assert yf.get_quote.call_count == 1
