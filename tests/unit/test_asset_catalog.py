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
