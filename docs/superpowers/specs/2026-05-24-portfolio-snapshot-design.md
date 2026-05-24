# Design: Portfolio Snapshot from Extrato de Conta

**Data:** 2026-05-24  
**Status:** Approved

## Contexto

Ao importar um extrato de conta de investimento (ex: extrato XP/Rico `021677760.pdf`), o usuário quer:
1. Salvar as transações individuais (COMPRA/VENDA) no banco
2. Salvar um **snapshot** das posições na data final do período
3. Ter renda fixa (CDBs) representada como tipo de ativo dedicado
4. O agente poder consultar o snapshot para responder "quanto tenho de X hoje?"

## Decisões de design

| Questão | Decisão |
|---|---|
| O que armazenar? | Transações + snapshot de posições |
| Renda fixa? | Novo tipo `FixedIncomePosition` no snapshot (nome, emissor, vencimento, valor) |
| Data do snapshot? | Data final do período do extrato |
| Agente usa snapshot? | Sim — pode consultar diretamente |
| Quantos LLM calls? | Um único call que extrai transações + posições + data do período |

## Arquitetura

```
extrato.pdf
    │
    ▼
document_ingestor_node
    │  classify → "transactions"
    ▼
_extract_extrato_data(text) ── LLM (1 call) ──► {
    "period_end": "2026-05-22",
    "account_id_hint": "...",
    "transactions": [...compra/venda...],
    "equity_snapshot": [{"ticker":"ITUB4","quantity":12,"avg_cost_hint":39.38}, ...],
    "fixed_income_snapshot": [
        {"name":"CDB Banco Fibra","maturity":"...","invested":...,"rate":"...%CDI","current_value":...},
        ...
    ]
}
    │
    ▼
CLI: _handle_extrato_import(file, data)
    ├── Preview de transações encontradas
    ├── Confirmar? → TransactionRepository.save() para cada compra/venda de ações
    ├── Preview de snapshot de posições
    └── Confirmar? → PortfolioSnapshotRepository.save()
```

## Modelos de domínio novos

### EquityPositionSnapshot (Pydantic, sem ORM próprio — JSON no snapshot)
```python
class EquityPositionSnapshot(BaseModel):
    ticker: str
    quantity: Decimal
    avg_cost_hint: Optional[Decimal] = None  # do extrato, pode ser impreciso
```

### FixedIncomePosition (Pydantic, sem ORM próprio — JSON no snapshot)
```python
class FixedIncomePosition(BaseModel):
    name: str                          # "CDB Banco Fibra"
    issuer: Optional[str] = None       # "Banco Fibra"
    maturity_date: Optional[date] = None
    invested_amount: Decimal
    rate_description: Optional[str] = None  # "113% CDI"
    current_value: Decimal
```

### PortfolioSnapshot (Pydantic + ORM)
```python
class PortfolioSnapshot(BaseModel):
    id: str = Field(default_factory=new_id)
    account_id: str
    snapshot_date: date                # data final do período do extrato
    source_file: str
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    equity_positions: list[EquityPositionSnapshot] = []
    fixed_income_positions: list[FixedIncomePosition] = []
```

## ORM

```python
class PortfolioSnapshotORM(Base):
    __tablename__ = "portfolio_snapshots"
    id = Column(String, primary_key=True)
    account_id = Column(String, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    source_file = Column(String, nullable=False)
    imported_at = Column(DateTime, default=datetime.utcnow)
    equity_positions_json = Column(JSON, nullable=False, default=list)
    fixed_income_positions_json = Column(JSON, nullable=False, default=list)
```

## LLM Prompt — extrato

```
Extraia dados financeiros deste extrato. Retorne JSON estrito.

{
  "period_end": "YYYY-MM-DD",
  "transactions": [
    {"date":"YYYY-MM-DD","ticker":"XXXX4","type":"compra|venda","quantity":0.0,"price":0.0,"fees":0.0}
  ],
  "equity_snapshot": [
    {"ticker":"XXXX4","quantity":0.0,"avg_cost_hint":0.0}
  ],
  "fixed_income_snapshot": [
    {"name":"...","issuer":"...","maturity_date":"YYYY-MM-DD ou null","invested_amount":0.0,
     "rate_description":"...","current_value":0.0}
  ]
}

Regras:
- transactions: apenas eventos COMPRA e VENDA do período
- equity_snapshot: posições atuais em ações/ETFs/FIIs no final do período
- fixed_income_snapshot: CDBs, LCIs, LCAs, debêntures — sem ticker de bolsa
- avg_cost_hint pode ser null se não disponível
- Responda APENAS JSON, sem markdown.
```

## Repositório

```python
class PortfolioSnapshotRepository:
    def save(self, snap: PortfolioSnapshot) -> None
    def get_latest(self, account_id: str) -> Optional[PortfolioSnapshot]
    def get_equity_position(self, account_id: str, ticker: str) -> Optional[EquityPositionSnapshot]
    def list_snapshots(self, account_id: str) -> list[PortfolioSnapshot]
```

## Agente — nova tool `get_current_holdings`

O agente de portfólio terá uma tool que:
1. Primeiro tenta `HoldingComputer.compute_all()` (calculado de transações)
2. Se não houver transações → usa `PortfolioSnapshotRepository.get_latest()`
3. Sempre informa a fonte e a data de referência

## Correção necessária: bug de persistência de transações

O CLI atual imprime "Transações importadas com sucesso" mas **não chama `TransactionRepository.save()`**. 
Esta correção deve ser feita no mesmo PR.

## Fora de escopo

- Reconciliação entre snapshot e transações (ex: detectar divergência)
- Suporte a Tesouro Direto como tipo próprio (vai para `fixed_income_snapshot` por enquanto)
- Preço de mercado em tempo real no snapshot (armazenar só custo/quantidade)
- Multi-conta (sempre usa o `account_id` passado via `--account`)
