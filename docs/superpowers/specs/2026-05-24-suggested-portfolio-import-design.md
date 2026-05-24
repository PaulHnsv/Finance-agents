# Importação de "Carteira Sugerida" — Design

## Problema

O comando `uv run investimentos import` hoje só processa documentos com **transações** (notas de corretagem, OFX, CSV). Documentos do tipo "carteira sugerida / portfólio recomendado" (PDFs de relatórios de corretora, contendo perfil + lista de ativos + percentuais + teses) são classificados como `outro` e descartados.

Queremos que o mesmo comando `import` detecte e processe esse tipo de documento, extraindo:
1. Percentuais de alocação por **classe de ativo** (RF, Ações BR, etc.)
2. Percentuais de alocação por **ativo individual** (ticker → %)
3. **Tese curta** por ativo (1 linha) para uso futuro pelos agentes

## Objetivos do usuário

1. **Definir alocação-alvo** a partir do PDF, com confirmação antes de ativar
2. **Servir como contexto** para agentes em análises futuras (consulta sob demanda)

## Decisões de design

| Tema | Decisão |
|---|---|
| Detecção do tipo | Automática no comando `import` (roteador) |
| Granularidade | Extrair classe + ativo individual quando disponíveis |
| Substituição da alocação-alvo | Manter histórico (versões); importar como **rascunho**, ativar com confirmação |
| Privacidade / Extração | Tentar regex/parser determinístico primeiro; LLM apenas como fallback |
| Armazenamento de contexto | Resumo curto (ticker + tese 1 linha) no banco; agente consulta sob demanda |
| Abordagem arquitetural | **B — Domínio separado**: `SuggestedPortfolio` é entidade distinta de `PortfolioObjective` |

## Arquitetura

### Novo domínio: `SuggestedPortfolio`

Entidade separada de `PortfolioObjective`. Ativar uma sugestão **copia** para um novo `PortfolioObjective` (preservando histórico).

```python
class SuggestedAssetAllocation(BaseModel):
    ticker: str
    target_pct: Decimal
    thesis: Optional[str] = None  # 1 linha, opcional

class SuggestedClassAllocation(BaseModel):
    asset_class: AssetClass
    target_pct: Decimal

class SuggestedPortfolioStatus(str, Enum):
    DRAFT = "draft"      # importado, aguardando ativação
    ACTIVE = "active"    # ativo (copiado para PortfolioObjective)
    ARCHIVED = "archived"

class SuggestedPortfolio(BaseModel):
    id: str
    name: str                                              # ex: "Carteira XP 2026-Q1"
    source_file: str                                       # caminho original
    risk_profile_hint: Optional[RiskProfile] = None        # se detectado no PDF
    class_allocations: list[SuggestedClassAllocation]
    asset_allocations: list[SuggestedAssetAllocation]
    status: SuggestedPortfolioStatus = SuggestedPortfolioStatus.DRAFT
    imported_at: datetime
    activated_at: Optional[datetime] = None
```

**Notas:**
- Validação "soma 100%" é **mais permissiva**: documentos reais nem sempre fecham exatos 100%. Avisar (warning), não falhar.
- `class_allocations` e `asset_allocations` podem coexistir (ex: doc diz "30% Ações BR" e detalha quais ações).

### Roteamento no `document_ingestor`

`document_ingestor_node` vira um **classificador + despachador**:

```
extract_pdf(path) → text
classify_document(text) → "transactions" | "suggested_portfolio" | "unknown"
  ├─ "transactions"        → extract_transactions_node (atual)
  ├─ "suggested_portfolio" → extract_suggested_portfolio_node (novo)
  └─ "unknown"             → report e parar
```

Classificação:
1. **Heurística (rápida, sem LLM):** procura palavras-chave (`portfólio sugerido`, `carteira recomendada`, `perfil`, `alocação sugerida` vs `nota de corretagem`, `compra`, `venda`, `liquidação`)
2. **Fallback LLM** se heurística for ambígua

### Extração de carteira sugerida (parser-first)

`integrations/documents/suggested_portfolio_parser.py`:
1. Tenta regex para padrões comuns:
   - `(TICKER4)\s+(\d+(?:[,.]\d+)?)\s*%` → ativo individual
   - `(Ações Brasil|Renda Fixa|...)[:\s]+(\d+(?:[,.]\d+)?)\s*%` → classe
2. Se nada encontrado → chama LLM com prompt estruturado, schema JSON
3. Normaliza tickers (uppercase) e percentuais (Decimal)

### Watchlist / contexto para agentes

O resumo curto (ticker + tese) **já fica em `SuggestedPortfolio.asset_allocations[].thesis`** — não precisa de tabela separada. Os agentes consultam via método do repositório:

```python
class SuggestedPortfolioRepository:
    def get_active_thesis_for(self, ticker: str) -> Optional[str]: ...
    def list_recent_suggestions(self, limit: int = 5) -> list[SuggestedPortfolio]: ...
```

### Persistência (SQLAlchemy)

Nova tabela `suggested_portfolios` + tabela filha `suggested_portfolio_allocations`. Migração Alembic nova.

### CLI

O comando `import` continua igual. Após detecção:

```
$ uv run investimentos import carteira.pdf --account acc-1

📄 Documento detectado: Carteira Sugerida
  - 3 classes de ativos extraídas
  - 12 ativos individuais com tese

Pré-visualização:
  Ações BR        40%
  Renda Fixa      35%
  Internacional   25%

  ITUB4   5%  — "Banco com forte super app..."
  BBDC4   3%  — "..."
  ...

? Salvar como rascunho? [Y/n]
? Ativar como alocação-alvo agora? [y/N]
```

Ativação:
- Cria/sobrescreve `PortfolioObjective` a partir das `class_allocations`
- Marca `SuggestedPortfolio.status = ACTIVE`
- Arquiva sugestões anteriores ativas (`ARCHIVED`)

## Escopo fora desta entrega

- Comparação automática "minha carteira real vs sugerida" → próxima feature
- Re-processamento de docs antigos quando parser melhora → não há tabela de docs brutos
- Múltiplas sugestões ativas simultâneas → só uma por vez
- UI/Web — só CLI

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| PDFs muito variados → parser frágil | LLM como fallback; documentar formatos suportados |
| LLM extrai tickers inexistentes/inventados | Validar tickers contra `brapi.dev` antes de salvar; warning se desconhecido |
| Percentuais não somam 100% | Warning ao invés de erro; usuário decide |
| Documento contém dados sensíveis (CPF, valores em R$) | Parser-first reduz exposição; ao usar LLM, sanitizar (mascarar CPF, R$) antes |
| Classificação errada (sugestão vs transação) | Em caso de dúvida, perguntar ao usuário antes de processar |

## Arquivos a criar/alterar

**Novos:**
- `src/investimentos/domain/models.py` (+ classes `Suggested*`)
- `src/investimentos/domain/db.py` (+ ORM)
- `migrations/versions/<hash>_suggested_portfolios.py`
- `src/investimentos/integrations/documents/suggested_portfolio_parser.py`
- `src/investimentos/agents/document_ingestor.py` (refatorar para roteador) + extrair `extract_transactions_node` e `extract_suggested_portfolio_node`
- `src/investimentos/repository/suggested_portfolio_repo.py`
- `tests/integrations/test_suggested_portfolio_parser.py`
- `tests/agents/test_document_ingestor_routing.py`

**Alterar:**
- `src/investimentos/cli.py` — fluxo de confirmação dual (salvar rascunho + ativar)
- `src/investimentos/agents/state.py` — campos `extracted_suggestion` etc.
- `README.md` — documentar novo tipo de documento suportado

## Critérios de aceitação

1. `uv run investimentos import <pdf_carteira_sugerida>` detecta automaticamente e mostra preview
2. Usuário pode salvar como rascunho sem ativar
3. Ativação cria/atualiza `PortfolioObjective` correspondente
4. Tickers inválidos geram warning, não exceção
5. Parser determinístico cobre o PDF de exemplo (Carteira_Paulo_Henrique) sem LLM
6. Agentes podem consultar tese por ticker via repositório
7. Testes unitários do parser e do roteador passam
