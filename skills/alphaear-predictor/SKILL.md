---
name: alphaear-predictor
description: Market prediction skill using Kronos. Use when user needs finance market time-series forecasting or news-aware finance market adjustments.
---

# AlphaEar Predictor Skill

## Overview

This skill utilizes the Kronos model (via `KronosPredictorUtility`) to perform time-series forecasting and adjust predictions based on news sentiment.

## Capabilities

### 1. Forecast Market Trends

**Workflow:**
1.  **Generate Base Forecast**: Use `scripts/kronos_predictor.py` (via `KronosPredictorUtility`) to generate the technical/quantitative forecast.
2.  **Adjust Forecast (Agentic)**: Use the **Forecast Adjustment Prompt** in `references/PROMPTS.md` to subjectively adjust the numbers based on latest news/logic.

**Key Tools:**
-   `KronosPredictorUtility.get_base_forecast(df, lookback, pred_len, news_text)`: Returns `List[KLinePoint]`.

**Example Usage (Python):**

```python
from scripts.utils.kronos_predictor import KronosPredictorUtility
from scripts.utils.database_manager import DatabaseManager

db = DatabaseManager()
predictor = KronosPredictorUtility()

# Forecast (e.g., AAPL or 2330.TW)
forecast = predictor.predict("AAPL", horizon="7d")
print(forecast)
```


## Configuration

This skill requires the **Kronos** model and an embedding model.

### Shared Schema

本 skill 內含 vendored 版的 `alphaear_schema`（single source of truth 在 `skills/_shared/alphaear_schema/`）。修改 schema 必須在 `_shared/` 內編輯後跑 `python tools/sync_shared_schema.py`。

> 版本戳記: `skills/alphaear-predictor/scripts/alphaear_schema/__vendored__.py`

1.  **Kronos Model**:
    -   Ensure `exports/models` directory exists in the project root.
    -   Place trained news projector weights (e.g., `kronos_news_v1.pt`) in `exports/models/`.
    -   Or depend on the base model (automatically downloaded).

> [!CAUTION]
> **Model Security**: This skill loads model weights from `exports/models`. We use `weights_only=True` and only scan for the `kronos_news_*.pt` pattern. Ensure you only place trusted checkpoints in this directory.

2.  **Environment Variables**:
    -   `EMBEDDING_MODEL`: Path or name of the embedding model (default: `sentence-transformers/all-MiniLM-L6-v2`).
    -   `KRONOS_MODEL_PATH`: Optional path to override model loading.

## Dependencies

-   `torch`
-   `transformers`
-   `sentence-transformers`
-   `pandas`
-   `numpy`
-   `scikit-learn`

## Fine-tuning Guide (TW/US)

This skill now supports fine-tuning the `news_proj` layer on TW/US market data.

### Prerequisites

1. Ensure `data/signal_flux.db` has populated `stock_list` and `stock_prices` tables.
2. Install `feedparser` for RSS parsing: `pip install feedparser`

### Step 1: Build Dataset

```bash
python scripts/build_dataset.py --tickers auto --from 2024-01-01 --to 2026-06-30 --shock-threshold 2.0 --markets TW,US
```

This discovers price shocks, collects news via yfinance/RSS (no baidu), verifies causality with LLM, and writes `data/training_dataset.parquet`.

### Step 2: Train news_proj

```bash
python scripts/train_news_proj.py --dataset data/training_dataset.parquet --epochs 30 --lr 1e-3 --seed 42
```

This freezes the Kronos base model, trains only `news_proj`, and saves to `exports/models/kronos_news_v1_<timestamp>.pt`.

### Step 3: Evaluate

```bash
python scripts/evaluate_news_proj.py --model latest --us-only
```

Outputs a MAE table comparing base vs news-aware predictions.

### Cache Mode

Re-run dataset building without re-fetching news:

```bash
python scripts/build_dataset.py --tickers auto --cache-only
```

This reads from `search_cache` and `causality_cache.parquet` to skip already-collected items.
