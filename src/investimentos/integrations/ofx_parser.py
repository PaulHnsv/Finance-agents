"""OFX file parser — imports brokerage transactions."""
from decimal import Decimal
from pathlib import Path

def parse_ofx(file_path: Path) -> list[dict]:
    """
    Parse OFX file and return list of raw transaction dicts.
    Uses ofxparse library.
    """
    import ofxparse
    with open(file_path, "rb") as f:
        try:
            ofx = ofxparse.OfxParser.parse(f)
        except Exception:
            return []

    transactions = []
    accounts = ofx.account if hasattr(ofx, "account") else []
    if not isinstance(accounts, list):
        accounts = [accounts]
    for account in accounts:
        stmt = getattr(account, "statement", None)
        if stmt is None:
            continue
        for txn in getattr(stmt, "transactions", []):
            transactions.append({
                "id": getattr(txn, "id", ""),
                "date": getattr(txn, "date", None),
                "amount": Decimal(str(getattr(txn, "amount", 0))),
                "memo": getattr(txn, "memo", ""),
                "type": getattr(txn, "type", ""),
            })
    return transactions
