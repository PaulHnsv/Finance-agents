from investimentos.integrations.documents.document_classifier import classify_document


def test_classifies_nota_corretagem():
    text = "NOTA DE CORRETAGEM\nCompra de ITUB4 100 ações a R$ 30,00\nLiquidação D+2"
    assert classify_document(text) == "transactions"


def test_classifies_carteira_sugerida():
    text = "Portfólio Sugerido\nPerfil moderado\nAções Brasil: 40%\nITUB4 5%\nBBDC4 3%"
    assert classify_document(text) == "suggested_portfolio"


def test_classifies_unknown():
    assert classify_document("documento aleatório sem palavras-chave") == "unknown"


def test_empty_text():
    assert classify_document("") == "unknown"
