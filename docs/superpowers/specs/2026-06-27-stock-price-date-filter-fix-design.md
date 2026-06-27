# 2026-06-27 alphaear-stock TWSE API 日期過濾 Bug Fix

## Problem

`StockTools.get_stock_price(ticker, start_date, end_date)` 回傳的日期範圍與請求不符。

當 `end_date` 落在過去年份（例如 `2025-06-27`）時，TWSE API 的 `date` 參數（格式 `YYYYMM`）實際上只控制「哪一年哪一月」，但 TWSE 回傳的資料永遠是**最近一個完整月份**的民國年資料。因此即使請求 `202506`，TWSE 仍回傳民國 115 年（2026 年）的資料。

`get_stock_price` 收到遠端資料後，未經日期過濾就直接寫入資料庫，導致回傳的日期超出請求範圍。

## Root Cause

`stock_tools.py:180` 呼叫 `fetch_kline_with_fallback()` 後，直接把回傳的 DataFrame 寫入 DB，沒有用 `start_date` / `end_date` 過濾。

## Fix

在 `get_stock_price` 中，fetch 到 `df_remote` 後、寫入 DB 前，加上日期過濾：

```python
df_remote = df_remote.loc[
    (df_remote["date"] >= start_date) & (df_remote["date"] <= end_date)
].copy()
```

## Files Changed

- `skills/alphaear-stock/scripts/stock_tools.py` — `get_stock_price` 方法

## Testing

- 單元測試：傳入跨年日期範圍，驗證回傳資料嚴格落在範圍內
- 回歸測試：原有測試（`tests/test_stock.py`）仍需通過
