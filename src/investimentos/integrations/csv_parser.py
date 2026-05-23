"""Generic CSV parser for brokerage exports."""
import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from typing import Optional

@dataclass
class CsvColumnMapping:
    date_col: str = "Data"
    ticker_col: str = "Ativo"
    type_col: str = "Operação"
    qty_col: str = "Quantidade"
    price_col: str = "Preço"
    fees_col: Optional[str] = "Taxas"
    date_format: str = "%d/%m/%Y"

def parse_csv(file_path: Path, mapping: CsvColumnMapping | None = None) -> list[dict]:
    m = mapping or CsvColumnMapping()
    rows = []
    with open(file_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            try:
                qty_str = row.get(m.qty_col, "0").replace(".", "").replace(",", ".")
                price_str = row.get(m.price_col, "0").replace(".", "").replace(",", ".")
                fees_str = (row.get(m.fees_col, "0") or "0").replace(".", "").replace(",", ".")
                rows.append({
                    "date": datetime.strptime(row[m.date_col], m.date_format).date(),
                    "ticker": row[m.ticker_col].strip().upper(),
                    "type": row[m.type_col].strip().lower(),
                    "quantity": Decimal(qty_str),
                    "price": Decimal(price_str),
                    "fees": Decimal(fees_str),
                })
            except (KeyError, InvalidOperation, ValueError):
                continue
    return rows
