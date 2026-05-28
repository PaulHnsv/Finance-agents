import pytest
from investimentos.domain.ticker import (
    normalize_b3_ticker, normalize_for_yfinance, is_valid_b3_ticker,
)


def test_normalize_b3_ticker_uppercases_and_strips():
    assert normalize_b3_ticker(" itub4 ") == "ITUB4"


def test_normalize_b3_ticker_strips_sa_suffix():
    assert normalize_b3_ticker("ITUB4.SA") == "ITUB4"


def test_normalize_for_yfinance_appends_sa():
    assert normalize_for_yfinance("ITUB4") == "ITUB4.SA"


def test_normalize_for_yfinance_idempotent():
    assert normalize_for_yfinance("ITUB4.SA") == "ITUB4.SA"


@pytest.mark.parametrize("t", ["ITUB4", "PETR3", "ALUP11", "BBSE3", "WEGE3"])
def test_is_valid_b3_ticker_accepts_real_tickers(t):
    assert is_valid_b3_ticker(t)


@pytest.mark.parametrize("t", ["", "AAPL", "ITUB", "ITUB45", "123", "ITUB4.SA"])
def test_is_valid_b3_ticker_rejects_invalid(t):
    assert not is_valid_b3_ticker(t)
