# Schema-Driven Refactor — Design Spec

**Date**: 2026-05-27  
**Status**: Draft — awaiting review

## Problem

The current pipeline produces inconsistent, hard-to-test outputs:

1. **Non-determinism** — `chat()` doesn't pass `temperature`, so identical inputs yield different prose every run.
2. **"Missing data X" hallucinations** — when an input metric is `null` (e.g. `twr_pct`), the LLM dutifully complains it's missing because the prompt forwards the raw JSON and asks for analysis.
3. **Generic recommendations** — the analyst prompt receives only aggregate `%` and HHI, not per-asset context (name, sector, weight vs target). The LLM can only produce platitudes.
4. **Fragile asset classification** — `_guess_class()` uses ticker-suffix heuristics. The `AssetORM` catalog exists in the DB but is never consulted.
5. **Domain rules scattered** — asset class, ticker normalization (`.SA` suffix), product taxonomy (CDB/LCI/Tesouro) are reimplemented in multiple places.
6. **Two LLM hops** — `portfolio_analyst` produces prose, then `report_writer` rewrites that prose. Each hop adds drift and cost.

## Goal

Make every agent output a **typed, validated, schema-driven artifact** that:
- Is rendered deterministically to markdown (humans).
- Is queryable as data (automations, alerts, history).
- Is testable by asserting on fields (not regex on text).
- Evolves additively without breaking consumers.

## Approach

**Top-down structured output.** Define Pydantic schemas for every agent's output. Force the LLM to fill the schema via `response_format` (with prompt+Pydantic-validation fallback). Eliminate the second-pass LLM `report_writer` — replace with a pure-Python renderer.

The domain layer is hardened in parallel: a single `AssetCatalogService` is the only source of truth for ticker → asset class / sector / display name.

## Architecture

### New modules

| Module | Responsibility |
|---|---|
| `domain/asset_catalog.py` | `AssetCatalogService.classify(ticker) -> AssetClassification`. Reads `AssetORM`, falls back to yfinance industry, caches in memory. Single source of truth. |
| `domain/ticker.py` | `normalize_for_yfinance(ticker)`, `is_valid_b3_ticker(t)`. One place for `.SA` suffix and validation. |
| `llm/structured.py` | `chat_structured(messages, response_schema, model, temperature=0) -> T`. Calls `chat.completions.create` with `response_format`, validates with Pydantic, retries once with error-feedback on validation failure. |
| `agents/schemas/portfolio_report.py` | `PortfolioReport` and child schemas (`DiversificationFinding`, `DriftFinding`, `RiskFinding`, `NextStep`). |
| `agents/schemas/market_brief.py` | `MarketBrief` schema for the market analyst. |
| `agents/rendering/report_renderer.py` | Pure functions: `render_portfolio_report(r: PortfolioReport) -> str`. No LLM. |

### Modified modules

| Module | Change |
|---|---|
| `llm/client.py` | `chat()` accepts `temperature` (default `0.0`). |
| `agents/portfolio_data_loader.py` | Drops `_guess_class`. Uses `AssetCatalogService`. Enriches holdings with `asset_class`, `sector`, `display_name`. State now exposes per-position details, not only aggregate `allocation_pct`. |
| `agents/state.py` | Adds `portfolio_report: Optional[PortfolioReport]`, `market_brief: Optional[MarketBrief]`. `specialist_outputs: list[str]` is removed. |
| `agents/portfolio_analyst.py` | Returns `{"portfolio_report": PortfolioReport}` via `chat_structured`. Prompt receives enriched per-asset list + computed metrics; prompt explicitly instructs to use only the fields present. |
| `agents/market_analyst.py` | Same pattern with `MarketBrief`. |
| `agents/report_writer.py` | **Deleted**. Replaced by `report_renderer.render_full_report(portfolio_report, market_brief)` called from workflow. |
| `workflows/portfolio_query.py` | Final node is the deterministic renderer, not an LLM call. |

### Data flow (new)

```
coordinator → portfolio_data_loader (DB + catalog → enriched metrics)
            → portfolio_analyst (chat_structured → PortfolioReport)
            → [optional] market_analyst (chat_structured → MarketBrief)
            → report_renderer (pure Python → markdown)
```

### Schema sketches

```python
class AssetClassification(BaseModel):
    asset_class: AssetClass        # acao, fii, etf, renda_fixa, ...
    sector: Optional[str]
    display_name: str
    source: Literal["catalog", "yfinance", "heuristic"]

class HoldingDetail(BaseModel):
    ticker: str
    display_name: str
    asset_class: AssetClass
    sector: Optional[str]
    allocation_pct: float          # % of portfolio
    target_pct: Optional[float]    # from active SuggestedPortfolio, if any
    delta_pct: Optional[float]

class DiversificationFinding(BaseModel):
    hhi: float
    classification: Literal["concentrada", "moderada", "diversificada"]
    comment: str = Field(max_length=240)

class DriftFinding(BaseModel):
    asset_class: AssetClass
    actual_pct: float
    target_pct: float
    delta_pct: float
    severity: Literal["ok", "atencao", "rebalancear"]
    comment: str = Field(max_length=180)

class RiskFinding(BaseModel):
    ticker: Optional[str]          # None for systemic risks
    risk_type: Literal["concentracao", "drawdown", "liquidez", "setorial", "cambio"]
    description: str = Field(max_length=240)

class NextStep(BaseModel):
    action: str = Field(max_length=140)
    priority: Literal["alta", "media", "baixa"]
    rationale: str = Field(max_length=200)

class PortfolioReport(BaseModel):
    summary: str = Field(max_length=320)
    diversification: DiversificationFinding
    drift: list[DriftFinding]
    risks: list[RiskFinding] = Field(max_length=5)
    next_steps: list[NextStep] = Field(min_length=2, max_length=4)
    additional_notes: list[str] = Field(default_factory=list, max_length=3)  # extensibility hook
```

### Fallback contract for `chat_structured`

1. Send request with `response_format={"type": "json_schema", "json_schema": {...}}`.
2. If provider rejects or returns invalid JSON: retry with `response_format={"type": "json_object"}` + schema embedded in system prompt.
3. Validate response with Pydantic; on `ValidationError`, do **one** repair retry sending the error message back to the model.
4. After two failures, raise `StructuredOutputError`. Workflow surfaces a controlled fallback message (not a hallucinated report).

## Non-goals

- Versioning of schemas (single version for now; revisit if external consumers appear).
- TWR/cashflow tracking (separate spec — schema has `Optional` slot for future use).
- Live broker integration (separate spec; schema already supports it via additive fields).

## Migration strategy

Refactor lands in this order — each step independently shippable and testable:

1. Asset catalog + ticker normalization (no behavioral change yet; tests assert classification rules).
2. `chat_structured` infrastructure + `MarketBrief` (small schema first — proves the pattern end-to-end).
3. `PortfolioReport` schema + analyst rewrite + renderer; delete `report_writer`.
4. Data loader uses catalog; per-asset enrichment in state.
5. Determinism guards: `temperature=0` everywhere; `drop_nulls` helper before serializing metrics into prompts.

Backward-compat: CLI output stays markdown. Only internal contracts change.

## Open questions

- Does GitHub Models honor `response_format=json_schema` strictly for `gpt-4o-mini`? Validate empirically in step 2 — if not, the json_object fallback path is the default.
- Should `PortfolioReport` persist to a new `reports` table for historical queries? Out of scope here; design leaves the door open via `model_dump()`.

## Test strategy

- **Renderer tests** (pure, fast): construct `PortfolioReport` fixtures, assert markdown output.
- **Analyst tests** (LLM mocked): patch `chat_structured` to return fixtures, assert state changes.
- **Catalog tests**: assert ALUP11 → ACAO, HGLG11 → FII, KLBN11 → ACAO, CDB → RENDA_FIXA.
- **Contract tests** (marked `@pytest.mark.eval`, run on demand): hit real LLM, assert structural properties (high HHI → "concentrada", etc.).
