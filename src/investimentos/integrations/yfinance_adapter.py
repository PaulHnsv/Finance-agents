"""yfinance adapter — fallback and BDRs."""
from decimal import Decimal
import yfinance as yf

class YFinanceClient:
    def get_quote(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        info = t.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
        return {
            "ticker": ticker,
            "price": Decimal(str(price)),
            "name": info.get("longName") or info.get("shortName", ticker),
            "change_pct": Decimal(str(info.get("regularMarketChangePercent", 0))),
        }

    def get_historical(self, ticker: str, period: str = "1y", interval: str = "1d") -> list[dict]:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval=interval)
        return [
            {"date": str(idx.date()), "close": Decimal(str(row["Close"])), "volume": int(row["Volume"])}
            for idx, row in hist.iterrows()
        ]
