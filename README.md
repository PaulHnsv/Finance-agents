# Sistema de Agentes para Gestão Financeira Pessoal

> ⚠️ **Aviso Legal**: Este sistema é meramente informativo e não constitui recomendação de investimento regulada pela CVM. Consulte um profissional habilitado antes de tomar decisões de investimento.

Um sistema de agentes de IA para análise e acompanhamento de carteiras de investimentos brasileiras, com foco em privacidade: valores absolutos em R$ nunca são enviados ao LLM.

## Funcionalidades

- 📊 Análise de carteira (custo médio, TWR, volatilidade, drawdown, HHI)
- 🎯 Gestão de alocação-alvo com sugestão de rebalanceamento
- 📄 Importação de documentos (PDF de informes, OFX, CSV de corretoras)
- 🤖 Agentes especializados orquestrados por LangGraph
- 📋 Questionário de suitability para perfil de investidor
- 🔒 Privacidade: apenas percentuais e métricas relativas são enviados ao LLM

## Pré-requisitos

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) — gerenciador de pacotes
- Docker + Docker Compose (opcional, para Langfuse)
- Personal Access Token do GitHub com escopo `models:read` (gere em https://github.com/settings/tokens)

### Provider de IA

O sistema usa a **GitHub Models API** (`https://models.github.ai/inference`), serviço gratuito do GitHub para prototipagem, autenticado via PAT. Modelos default: `openai/gpt-4o` (análises) e `openai/gpt-4o-mini` (classificação de intent). Substituíveis via `LLM_MODEL_DEFAULT` / `LLM_MODEL_LIGHT`.

> ⚠️ GitHub Models tem rate limits agressivos (~50 req/dia no tier "high"). Para uso de produção, migre para Azure AI Foundry — o SDK é o mesmo, só muda `LLM_BASE_URL` e a chave.

## Quick Start

```bash
# 1. Clone e configure
git clone <repo>
cd "Finance agents"

# 2. Configure variáveis de ambiente
cp .env.example .env
# Edite .env e adicione: GITHUB_TOKEN=ghp_...

# 3. Instale dependências
uv sync

# 4. Crie o banco de dados
mkdir -p data
uv run alembic upgrade head

# 5. (Opcional) Suba Langfuse para observabilidade
docker-compose up -d langfuse
```

## Uso da CLI

```bash
# Consulta em linguagem natural
uv run investimentos query "como está a diversificação da minha carteira?"

# Relatório completo
uv run investimentos report
uv run investimentos report --output relatorio.md

# Importar documento
uv run investimentos import nota_corretagem.pdf --account acc-1
uv run investimentos import extrato.ofx --account acc-1

# Configurar perfil de investidor
uv run investimentos profile

# Configurar objetivo de alocação
uv run investimentos objective
```

## Arquitetura

```
src/investimentos/
├── config.py                    # Settings com pydantic-settings
├── domain/
│   ├── models.py                # Modelos Pydantic (Account, Asset, Transaction, etc.)
│   └── db.py                    # ORM SQLAlchemy
├── repository/                  # CRUD + HoldingComputer
├── integrations/                # brapi.dev, yfinance, OFX, CSV, PDF, Tesouro Direto
├── tools/                       # Cálculos: custo médio, TWR, volatilidade, drift
├── agents/                      # Agentes LLM (coordinator, portfolio, market, etc.)
├── llm/                         # Client LLM provider-agnostic (GitHub Models)
├── workflows/                   # LangGraph StateGraph
├── flows/                       # Fluxos interativos (suitability, objetivo)
└── cli.py                       # Entrypoint Typer
```

### Fluxo principal

```
CLI query
  └─► Coordinator (classifica intent)
        ├─► Portfolio Analyst (métricas % + HHI + drift)
        │     └─► Market Analyst (cotações + contexto)
        │           └─► Report Writer (relatório final markdown)
        ├─► Market Analyst (consulta direta de mercado)
        └─► Document Ingestor (extração de transações)
```

## Rodando testes

```bash
$env:PYTHONPATH="src"
uv run pytest tests/ -v
uv run pytest tests/ --cov=src/investimentos --cov-report=term-missing
```

## Roadmap

- **Fase 1 (atual):** MVP — análise de carteira, importação, CLI
- **Fase 2:** Integração com Open Finance (Banco Central)
- **Fase 3:** Relatórios IR (DARF, GCAP)
- **Fase 4:** Planejamento financeiro (reserva de emergência, dívidas)
