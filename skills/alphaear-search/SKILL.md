---
name: alphaear-search
description: Perform finance web searches and local context searches. Use when the user needs general finance info from the web (Jina/DDG/Baidu/Google) or needs to retrieve finance information from a local document store (RAG). Supports US and TW market auto-detection with real-time stock prices.
---

# AlphaEar Search Skill

## Overview

Unified search capabilities supporting multiple search engines with automatic market detection for US and TW stocks.

## Capabilities

### 1. Web Search

Use `scripts/search_tools.py` via `SearchTools`.

-   **Search**: `search(query, engine, max_results, market)`
    -   Engines: `jina`, `ddg`, `baidu`, `google`, `local`.
    -   Market: auto-detect (`us`/`tw`) or manual override via `market` param.
    -   Returns: JSON string (summary) or List[Dict] (via `search_list`).
-   **Aggregate**: `aggregate_search(query)`
    -   Combines results from multiple engines.

### 2. Market Detection

Automatic market type detection based on query content:
-   TW stocks: 4-digit stock codes (2330) or company names (台積電).
-   US stocks: ticker symbols (AAPL, NVDA) or company names (蘋果, Meta).

### 3. Engine Selection

| Market | Primary Engine | Fallback |
|--------|---------------|----------|
| US     | jina          | ddg      |
| TW     | google        | ddg      |
| Unknown| default       | ddg      |

### 4. Real-time Stock Price

Search results are enriched with real-time stock prices via `yfinance`:
-   US stocks: ticker symbol (e.g., `AAPL`).
-   TW stocks: ticker with `.TW` suffix (e.g., `2330.TW`).
-   Price data: `price`, `currency`, `change`, `change_pct`.

### 5. Local RAG

Use `scripts/hybrid_search.py` or `SearchTools` with `engine='local'`.

-   **Search**: Searches local `daily_news` database with BM25 + vector hybrid search.

## Dependencies

-   `duckduckgo-search`, `requests`, `yfinance`
-   `scripts/database_manager.py` (search cache & local news)
-   `scripts/utils/humanize.py` (optional, from lab-drawer humanizer)
