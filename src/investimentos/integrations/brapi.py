"""brapi.dev client — B3 quotes and fundamentals."""
import httpx
from decimal import Decimal

BASE_URL = "https://brapi.dev/api"

class BrapiClient:
    def __init__(self, token: str = "", timeout: int = 15):
        self.token = token
        self.timeout = timeout

    def _params(self, **extra) -> dict:
        p = {"token": self.token} if self.token else {}
        p.update(extra)
        return p

    def get_quote(self, ticker: str) -> dict:
        url = f"{BASE_URL}/quote/{ticker.upper()}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, params=self._params())
            resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            raise ValueError(f"No data for ticker {ticker}")
        r = results[0]
        return {
            "ticker": r.get("symbol"),
            "price": Decimal(str(r.get("regularMarketPrice", 0))),
            "change_pct": Decimal(str(r.get("regularMarketChangePercent", 0))),
            "volume": r.get("regularMarketVolume"),
            "name": r.get("longName") or r.get("shortName"),
        }

    def get_quotes(self, tickers: list[str]) -> list[dict]:
        joined = ",".join(t.upper() for t in tickers)
        url = f"{BASE_URL}/quote/{joined}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, params=self._params())
            resp.raise_for_status()
        data = resp.json()
        return [
            {
                "ticker": r.get("symbol"),
                "price": Decimal(str(r.get("regularMarketPrice", 0))),
                "change_pct": Decimal(str(r.get("regularMarketChangePercent", 0))),
                "name": r.get("longName") or r.get("shortName"),
            }
            for r in data.get("results", [])
        ]
