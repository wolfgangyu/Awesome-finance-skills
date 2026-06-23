---
name: alphaear-stock
description: Search US/Taiwan finance stock tickers and retrieve historical OHLCV prices and fundamentals. Use when user asks about US or Taiwan stock codes, recent price changes, or specific company finance stock info.
---

# AlphaEar Stock Skill

## Overview

Search US and Taiwan (TWSE/TPEx) stock tickers and retrieve historical price data (OHLCV) and company fundamentals.

不再支援：
- A 股 / 港股（akshare 與 EastMoneyDirect 已移除）

## Capabilities

### 1. Stock Search & Data

Use `scripts/stock_tools.py` via `StockTools`.

- **Search**: `search_ticker(query)`
  - Fuzzy search by code or name (e.g., "2330", "AAPL", "台積電", "Apple").
  - Returns: List of `{code, name}`.
- **Get Price**: `get_stock_price(ticker, start_date, end_date)`
  - US stocks: `yfinance`
  - Taiwan stocks: TWSE (上市) / TPEx (上櫃) 官方 HTTP
  - Returns DataFrame with `date, open, close, high, low, volume, change_pct`.
  - Dates format: `"YYYY-MM-DD"`.
- **Get Fundamentals**: `get_stock_fundamentals(ticker)`
  - US stocks: yfinance
  - Taiwan stocks: 暫時回空 dict（後續規畫整合 My-TW-Coverage）
  - Returns dict with `name, sector, industry, market_cap, pe_ratio, summary, currency`.

### 2. Taiwan Detector

- `from scripts.stock_tools import detect_market`
- `detect_market("2330")` → `"twse"`
- `detect_market("6488")` → `"twse"` (會 fallback 到 TPEx)
- `detect_market("AAPL")` → `"us"`

## Dependencies

- `pandas`, `requests`, `yfinance`
- `loguru` (logging)
- `scripts/database_manager.py` (stock tables)
- `scripts/twse_client.py` (TWSE / TPEx HTTP client)

## Notes

- **US stocks (yfinance)**: 若無法存取 Yahoo Finance，可設定 proxy：
  ```bash
  export HTTP_PROXY="http://<proxy_ip>:<port>"
  export HTTPS_PROXY="http://<proxy_ip>:<port>"
  ```
- **Taiwan stocks (TWSE/TPEx)**: 走官方 HTTP，無需 API key。
  - TWSE: `https://www.twse.com.tw/exchangeReport/STOCK_DAY`
  - TPEx: `https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/stock_day.php`
  - 4 位純數字代號一律先試 TWSE；空資料時 fallback TPEx。
  - 月報格式以 `end_date` 為查詢錨點（TWSE 單次回傳單月資料）。
- **舊相容性**：移除 `akshare` / `EastMoneyDirect` 後，凡函式對 A 股/港股代碼會回空 DataFrame（**不 raise**），呼叫端需自行判斷。
