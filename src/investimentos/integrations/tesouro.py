"""Tesouro Direto official API client."""
import httpx
from decimal import Decimal

BASE_URL = "https://www.tesourodireto.com.br/json/br/com/b3/tesouro/security/pu/getAllSecurityPrice.json"

def get_tesouro_prices() -> list[dict]:
    """Fetch all current Tesouro Direto prices from official API."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(BASE_URL)
        resp.raise_for_status()
    data = resp.json()
    securities = (
        data.get("response", {})
        .get("TrsrBdTradgList", [])
    )
    result = []
    for s in securities:
        bond = s.get("TrsrBd", {})
        result.append({
            "name": bond.get("nm"),
            "maturity": bond.get("mtrtyDt"),
            "buy_price": Decimal(str(bond.get("invstmtStbl", {}).get("untrInvstmtVal", 0))),
            "sell_price": Decimal(str(bond.get("redVal", 0))),
            "annual_rate": Decimal(str(bond.get("anulInvstmtRate", 0))),
        })
    return result
