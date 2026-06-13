from investimentos.agents.query_intent import is_direct_holdings_question


def test_detects_direct_stock_list_question():
    assert is_direct_holdings_question("quais ações tenho na minha carteira?")


def test_does_not_detect_why_question_as_direct_holdings():
    assert not is_direct_holdings_question("porque tenho muitas ações?")


def test_does_not_detect_specific_ticker_position_as_direct_holdings():
    assert not is_direct_holdings_question("qual minha posição em PETR4?")
