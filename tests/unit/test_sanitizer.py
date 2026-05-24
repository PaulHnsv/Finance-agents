from investimentos.integrations.documents.sanitizer import sanitize


def test_masks_cpf():
    assert sanitize("CPF: 123.456.789-00") == "CPF: [CPF]"


def test_masks_cnpj():
    assert sanitize("CNPJ: 12.345.678/0001-90") == "CNPJ: [CNPJ]"


def test_masks_email():
    assert sanitize("contato@banco.com.br") == "[EMAIL]"


def test_masks_phone():
    assert sanitize("(11) 99999-1234") == "[TEL]"
    assert sanitize("(11) 3333-4444") == "[TEL]"


def test_masks_monetary_value():
    assert sanitize("Total: R$ 1.234,56") == "Total: R$[VALOR]"
    assert sanitize("saldo R$500,00") == "saldo R$[VALOR]"


def test_preserves_ticker():
    assert "ITUB4" in sanitize("COMPRA ITUB4 10 39,38")


def test_preserves_date():
    assert "22/05/2026" in sanitize("Data: 22/05/2026")


def test_preserves_percentage():
    assert "7,5%" in sanitize("yield entre 6,5% e 7,5%")


def test_masks_large_account_number():
    result = sanitize("conta 021677760")
    assert "021677760" not in result


def test_multiple_rules():
    text = "CPF 123.456.789-00 saldo R$ 5.000,00 email@test.com"
    result = sanitize(text)
    assert "[CPF]" in result
    assert "R$[VALOR]" in result
    assert "[EMAIL]" in result
    assert "123.456.789-00" not in result
    assert "5.000,00" not in result
