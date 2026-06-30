# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Awesome Finance Skills** is a collection of independent, distributable Agent skills — not a single application.

- Each `skills/<skill-name>/` is a self-contained skill (loadable by OpenAI/Claude/Agno frameworks).
- Each skill ships with `SKILL.md` (YAML frontmatter `name`+`description` + Markdown body) and optional `scripts/`, `references/`, `assets/` resources.
- Users install a single skill via `npx skills add RKiding/Awesome-finance-skills@<skill-name>`, or copy all `skills/*` into their agent's skill directory.
- The upstream framework is [DeepEar (AlphaEar)](https://github.com/RKiding/AlphaEar); this repo is the "decayed skill slice."

## Data Flow

Skills are independent but compose into a pipeline:

```
alphaear-stock  ->  stock prices & tickers (TWSE/TPEx/yfinance)
alphaear-news   ->  aggregated financial news (10+ sources)
alphaear-search ->  web search + local RAG
alphaear-sentiment ->  text sentiment (-1.0 ~ +1.0)
alphaear-predictor ->  Kronos time-series forecasting
alphaear-signal-tracker ->  InvestmentSignal lifecycle (strengthen/weaken/falsify)
alphaear-reporter ->  research reports (composes all above)
alphaear-logic-visualizer ->  Draw.io XML diagrams
alphaear-deepear-lite ->  lightweight DeepEar signal fetcher
```

## Import Layout Warning

The `scripts/` subdirectory layout is **not consistent** across skills. Always `ls <skill>/scripts/` before editing.

| Type | Packages | Layout |
|:-----|:-----|:-----|
| "flat" | `alphaear-news`, `alphaear-stock`, `alphaear-sentiment`, `alphaear-search`, `alphaear-deepear-lite`, `alphaear-logic-visualizer` | `scripts/<tool>.py`, `scripts/database_manager.py`; intra-module imports use `from .database_manager import DatabaseManager` |
| "nested" | `alphaear-predictor`, `alphaear-signal-tracker`, `alphaear-reporter` | `scripts/*.py` is entry/agent; `scripts/{utils,prompts,schema,tools,predictor}/` contains implementations; inter-module imports use `from .utils.xxx` |

## Development Commands

```bash
# Run a skill's smoke test (unittest, adds skill dir to sys.path)
python3 tests/alphaear-news/test_news.py
python3 tests/alphaear-stock/test_stock.py
python3 tests/alphaear-predictor/test_predictor.py
python3 tests/alphaear-reporter/test_reporter.py
python3 skills/alphaear-signal-tracker/tests/test_tracker.py
python3 skills/alphaear-logic-visualizer/tests/test_visualizer.py

# DeepEar Lite connectivity smoke test
python3 skills/alphaear-deepear-lite/scripts/deepear_lite.py

# Map news source IDs
cat skills/alphaear-news/references/sources.md

# Sync shared schema to all vendored skills
python3 tools/sync_shared_schema.py --check   # dry-run: report drift only
python3 tools/sync_shared_schema.py            # apply sync

# Convert simplified Chinese to zh-TW / check remaining
python3 tools/convert_zh_tw.py [paths...] --include-py
python3 tools/check_zh_tw.py [paths...] --include-py  # exit 1 = remaining issues
```

Test convention: `scripts.xxx_tools` is the entry class; `scripts.database_manager` provides SQLite (default `data/signal_flux.db`, tests typically use `DatabaseManager(":memory:")`).

## Architecture: Shared Abstractions

- **Data models (core)**: See `skills/_shared/alphaear_schema/models.py` for `InvestmentSignal`, `TransmissionNode`, `ForecastResult`, `KLinePoint`, `ResearchContext`, `InvestmentReport`, `FilterResult`, `SignalCluster`. Other skills (reporter, signal-tracker) vendor copies — **changing a schema requires syncing to 3 places** via `tools/sync_shared_schema.py`.
- **Database**: Each skill declares its own `data/signal_flux.db` with table structures (`daily_news`, `search_cache`, `search_detail`, quote tables) in its own `scripts/database_manager.py`. This is intentional for skill independence. Adding columns uses `ALTER TABLE` with error tolerance within each skill, not centralized migration.
- **LLM abstraction**: `scripts/llm/{router,factory,capability}.py` routes by capability to Anthropic / OpenAI / Gemini. Shared by `alphaear-search` and `alphaear-sentiment`; reporter/signal-tracker use their own variants.

## Do NOT Introduce

Banned or removed technologies. Do not re-add these:

- **`akshare`** — Removed in v1.1.0 market refactor (A-share/HK-stock support dropped).
- **`EastMoneyDirect`** — Removed alongside akshare.
- **BERT / FinBERT** — Stripped from signal-tracker, reporter, and search_tools in recent commits. Do not re-introduce ML sentiment models.
- **Arbitrary `.pt` model files** — `alphaear-predictor` only loads from `exports/models/` matching `kronos_news_*.pt` with `weights_only=True`. Never load random `.pt` files.
- **Shared `DatabaseManager`** — Each skill must keep its own DB schema; do not consolidate into a single database.

## Security Notes

- `alphaear-predictor`: Kronos weights only from `exports/models/`, locked to `kronos_news_*.pt` + `weights_only=True`.
- US stock data uses `yfinance`; Taiwan users may need `HTTP_PROXY` / `HTTPS_PROXY` env vars.

## Testing Strategy

`tests/<skill>/` contains smoke tests that verify import/class initialization only (fail-soft when LLM/models are unavailable). Heavy model and network tests (`alphaear-predictor` loading Kronos, `alphaear-stock` hitting yfinance/TWSE/TPEx) typically won't pass locally:

- When modifying schemas or contracts, run `tests/<skill>/test_*.py` to verify the import stage doesn't crash.
- For actual networking/heavy-model changes, verify in staging or manually; do not claim "passed."

## Known Pitfalls

- SKILL.md body may have duplicate section headings (e.g., `alphaear-predictor` had two `### 1. Forecast Market Trends`) — check for duplicates before adding capability sections.
- SKILL.md example code may not match actual import paths; trust the file system (`ls <skill>/scripts/`) over documentation.
- `signal-tracker` was extracted from FinAgent; it's a pattern, not yet fully standalone. Check `scripts/fin_agent.py::track_signal` before modifying.
- When SKILL.md examples and actual code disagree, trust the actual file layout.

## My Working Style

- **First principles**: Debug bugs from first principles, not guesswork.
- **Plan before action**: Before important development steps, produce a plan (use `using-superpowers` skill) before executing.
- **Open source first**: Use existing open-source packages; don't reinvent wheels.
- **Verify before claiming**: Evidence before assertions. If tests fail, report the output — don't claim success.
- **Compress = fleeting note**: Before context compression, write a fleeting note to `~/.claude/projects/<project>/memory/` capturing conversation highlights.
