# Migração: Anthropic SDK → GitHub Models API

**Status:** Design aprovado, pronto para planejamento de implementação
**Data:** 2026-05-23
**Autor:** Paulo + Copilot CLI (brainstorming)

---

## 1. Problema

O projeto `investimentos` hoje depende exclusivamente da **API da Anthropic** (`anthropic>=0.40.0` + `langchain-anthropic>=0.3.0`) para todos os agents LangGraph:

- `coordinator.py` — classificação de intent (modelo light)
- `portfolio_analyst.py` — análise de métricas (modelo default)
- `market_analyst.py` — contexto de mercado (modelo default)
- `report_writer.py` — síntese de relatório (modelo default)
- `document_ingestor.py` — extração estruturada de PDFs (modelo default)

Isso obriga o usuário a manter uma chave paga da Anthropic separada da sua assinatura do GitHub Copilot Pro, que ele já paga.

### Restrição importante de viabilidade

Usar o endpoint interno do GitHub Copilot (`api.githubcopilot.com/chat/completions`) como LLM genérico **viola os Termos de Uso do produto**, que restringem o Copilot a sugestões e chat dentro de IDEs suportados. Essa rota foi descartada.

A alternativa **oficial, legítima e gratuita para prototipagem** que reaproveita a infraestrutura de IA do GitHub é o **GitHub Models** (`https://models.github.ai/inference`), autenticado com um PAT do GitHub, compatível com o protocolo OpenAI.

---

## 2. Objetivo

Substituir a Anthropic pelo GitHub Models como provider LLM padrão, mantendo:

- A arquitetura LangGraph atual (state, nodes, edges) intacta
- Os prompts em português inalterados
- A garantia de privacidade (nenhum valor absoluto em R$ enviado ao LLM)
- A possibilidade de trocar de provider sem reescrever agents (provider-agnostic)

Como não-objetivos explícitos:

- Não vamos suportar múltiplos providers simultaneamente nesta migração
- Não vamos migrar para Azure AI Foundry nesta fase (fica como caminho de "produção" futuro)
- Não vamos alterar prompts, fluxo de agents ou modelo de dados

---

## 3. Abordagem escolhida

**Trocar `anthropic` SDK por `openai` SDK apontando para o endpoint do GitHub Models**, porque:

1. GitHub Models é OpenAI-compatible em `/chat/completions` — mudança de código é mínima
2. Mantém um caminho de upgrade trivial para Azure OpenAI / Azure AI Foundry (mesmo SDK, só muda `base_url` e auth)
3. Permite trocar provider futuramente sem mexer em agents, isolando o cliente em um módulo único

### Decisão de arquitetura: factory centralizada

Criar `src/investimentos/llm/client.py` com:

```python
def get_llm_client() -> OpenAI: ...
def chat(messages: list[dict], *, model: str, max_tokens: int) -> str: ...
```

Todos os 5 agents passam a chamar `chat(...)` em vez de instanciar `Anthropic()` localmente. Isso:

- Elimina duplicação (hoje cada agent instancia o client + faz `.content[0].text.strip()`)
- Centraliza retry/rate-limit handling em um único lugar
- Facilita mock em testes
- Permite trocar provider editando 1 arquivo

### Mapeamento de modelos

| Hoje (config) | Equivalente GitHub Models |
|---|---|
| `claude-sonnet-4-6` (default) | `openai/gpt-4o` ou `anthropic/claude-3-5-sonnet` |
| `claude-haiku-4-5` (light) | `openai/gpt-4o-mini` ou `anthropic/claude-3-5-haiku` |

> **Nota:** GitHub Models pode oferecer modelos Anthropic, mas catálogo varia. A escolha final entre GPT-4o e Claude via GH Models fica como variável de ambiente, default = `openai/gpt-4o-mini` (light) e `openai/gpt-4o` (default), porque GPT tem maior estabilidade de disponibilidade no catálogo do GH Models.

---

## 4. Rate limits — análise de impacto

GitHub Models tem limites por minuto/dia/tokens. Para conta Copilot Pro (referência, sujeita a mudança):

| Tier | req/min | req/dia | tokens in | tokens out |
|---|---|---|---|---|
| Low (gpt-4o-mini) | ~15 | ~150 | 8.000 | 4.000 |
| High (gpt-4o) | ~10 | ~50 | 8.000 | 4.000 |

### Impacto por componente

| Componente | Risco | Mitigação |
|---|---|---|
| `coordinator_node` (20 tokens out) | Baixíssimo | — |
| `portfolio_analyst_node` (600 tokens out) | Baixo | — |
| `market_analyst_node` (500 tokens out) | Baixo | — |
| `report_writer_node` (1500 tokens out) | **Médio** — pode exceder `4000` se prompt crescer | Manter `max_tokens=1500`, validar em testes |
| `document_ingestor_node` (PDF até 8k chars) | **Alto** — PDFs grandes podem ultrapassar 8k tokens input | Já trunca em `text[:8000]` chars (~2k tokens), mas precisamos chunking futuro |
| APScheduler jobs | Médio | Documentar no README que jobs frequentes podem bater no limite diário |

### Estratégia de retry

Adicionar backoff exponencial no `chat()` para erros 429 (rate limit) — máx. 3 tentativas com jitter. Implementar via `tenacity` (já é dep transitiva de `langchain`).

---

## 5. Mudanças concretas

### 5.1 Dependências (`pyproject.toml`)

```diff
-    "anthropic>=0.40.0",
-    "langchain-anthropic>=0.3.0",
+    "openai>=1.54.0",
+    "tenacity>=9.0.0",
```

> `langchain-openai` só será adicionado se houver código LangChain que dependa do binding (a checar; hoje os agents usam SDK direto, não LangChain LLM wrappers).

### 5.2 Configuração (`src/investimentos/config.py`)

```diff
-    anthropic_api_key: str
+    github_token: str
+    llm_base_url: str = "https://models.github.ai/inference"
-    llm_model_default: str = "claude-sonnet-4-6"
-    llm_model_light: str = "claude-haiku-4-5"
+    llm_model_default: str = "openai/gpt-4o"
+    llm_model_light: str = "openai/gpt-4o-mini"

-    @field_validator("anthropic_api_key")
+    @field_validator("github_token")
     @classmethod
     def api_key_must_not_be_empty(cls, v: str) -> str:
         if not v:
-            raise ValueError("ANTHROPIC_API_KEY must not be empty")
+            raise ValueError("GITHUB_TOKEN must not be empty")
         return v
```

### 5.3 Novo módulo `src/investimentos/llm/client.py`

```python
"""Provider-agnostic LLM client. Today: GitHub Models (OpenAI-compatible)."""
from functools import lru_cache
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError
from investimentos.config import get_settings


@lru_cache
def get_llm_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(base_url=settings.llm_base_url, api_key=settings.github_token)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def chat(messages: list[dict], *, model: str, max_tokens: int) -> str:
    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()
```

### 5.4 Cada agent (`coordinator.py`, `portfolio_analyst.py`, `market_analyst.py`, `report_writer.py`, `document_ingestor.py`)

Padrão de mudança (exemplo `coordinator.py`):

```diff
-from anthropic import Anthropic
+from investimentos.llm.client import chat
 from investimentos.agents.state import AgentState
 from investimentos.config import get_settings

 def coordinator_node(state: AgentState) -> dict:
     settings = get_settings()
-    client = Anthropic(api_key=settings.anthropic_api_key)
-    response = client.messages.create(
-        model=settings.llm_model_light,
-        max_tokens=20,
-        messages=[{
-            "role": "user",
-            "content": INTENT_PROMPT.format(query=state.user_query),
-        }],
-    )
-    intent = response.content[0].text.strip().lower()
+    intent = chat(
+        messages=[{"role": "user", "content": INTENT_PROMPT.format(query=state.user_query)}],
+        model=settings.llm_model_light,
+        max_tokens=20,
+    ).lower()
     ...
```

Mesma transformação para os outros 4 agents.

### 5.5 Variáveis de ambiente

```diff
# .env
-ANTHROPIC_API_KEY=sk-ant-...
+GITHUB_TOKEN=ghp_...
+# Opcional: LLM_BASE_URL=https://models.github.ai/inference
+# Opcional: LLM_MODEL_DEFAULT=openai/gpt-4o
+# Opcional: LLM_MODEL_LIGHT=openai/gpt-4o-mini
```

### 5.6 Testes (`tests/unit/test_config.py` + novos)

- Atualizar `test_config.py` para validar `github_token` em vez de `anthropic_api_key`
- Adicionar `tests/unit/test_llm_client.py` com mock de `OpenAI.chat.completions.create` validando: chamada com params corretos, parsing de resposta, retry em `RateLimitError`
- Verificar se há testes de agents que mockam `Anthropic` — atualizar para mockar `investimentos.llm.client.chat`

### 5.7 README + docs

- Substituir referências a `ANTHROPIC_API_KEY` por `GITHUB_TOKEN`
- Adicionar instruções para gerar PAT do GitHub com escopo `models:read`
- Adicionar nota sobre rate limits e que é "prototyping tier"
- Documentar a migração futura para Azure AI Foundry como path de produção

---

## 6. Plano de teste (validação)

1. **Smoke test manual:** rodar `uv run investimentos query "como está a diversificação da minha carteira?"` com dados de exemplo, validar que a resposta sai coerente
2. **Suite de testes:** `uv run pytest` deve passar 100%
3. **Test de cada agent isoladamente:** garantir que cada um retorna formato esperado
4. **Test de rate limit:** simular 429 e validar que retry funciona
5. **Smoke test de ingestão:** importar um PDF de exemplo e validar extração JSON

---

## 7. Riscos & mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Catálogo do GH Models muda nomes de modelos | Média | Modelo configurável via env; documentar como listar catálogo |
| Limite diário (~50 req high) atrapalha uso pesado | Média | Usar `gpt-4o-mini` (tier low, ~150/dia) onde possível; documentar |
| Diferenças sutis de output entre Claude e GPT (formatting markdown, JSON) | Alta | Validar prompts via smoke tests; ajustar prompts se necessário |
| GH Models é "beta/prototyping" — pode sair do ar | Baixa | Path documentado para Azure AI Foundry (mesmo SDK) |
| Erro de JSON parsing no `document_ingestor` (GPT às vezes embrulha em markdown) | Alta | Adicionar limpeza de fences ```json ... ``` antes de `json.loads`; já é boa prática |

---

## 8. Out of scope (explicitamente)

- Suporte multi-provider simultâneo
- Migração para Azure AI Foundry
- Refatoração do LangGraph state machine
- Mudanças de prompts (exceto correções pontuais se smoke tests falharem)
- Caching de respostas LLM
- Streaming de respostas

---

## 9. Próximos passos

1. Spec aprovada → invocar skill `writing-plans` para gerar plano detalhado de implementação com TODOs
2. Implementação incremental (1 agent por vez, começando pelo `coordinator` que é o mais simples)
3. Smoke test end-to-end antes de remover deps antigas
