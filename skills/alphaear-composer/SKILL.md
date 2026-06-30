# AlphaEar Composer Skill

自動從原始資料（新聞、搜尋、股價）組裝成 `latest.json` 格式的投資訊號報告。

## 功能

- **`compose_latest(days=1, market="both")`** — 執行完整 pipeline：讀取 DB → 形成訊號 → 產出 latest.json
- **`fetch_latest_signals(source="local")`** — 讀取 latest.json 並格式化為文字報告（與 alphaear-deepear-lite 介面相容）

## 兩種模式

| 模式 | 說明 | 適用場景 |
|------|------|----------|
| **Heuristic**（預設） | 從新聞數量、sentiment、價格波動自動計算 ISQ 分數 | 不需要 LLM API，快速原型 |
| **LLM** | 調用 LLM 產生更精確的 signal reasoning 和 ISQ 評分 | 高品質分析 |

## 輸出格式

產出的 `data/latest.json` 與 DeepEar Lite 的 `latest.json` 結構完全一致：

```json
{
  "generated_at": "2026-06-30T23:00:00+08:00",
  "run_id": "composer_20260630_230000",
  "count": 3,
  "signals": [
    {
      "signal_id": "2330.TW",
      "title": "台積電 Q2 營收創新高",
      "summary": "...",
      "reasoning": "...",
      "transmission_chain": [...],
      "sentiment_score": 0.75,
      "confidence": 0.8,
      "intensity": 4,
      "sources": [...]
    }
  ],
  "charts": {}
}
```

## 依賴

- `requests`, `loguru`
- shared schema: `scripts.alphaear_schema.models`
- LLM router（可選，LLM 模式需要）

## 驗證

```bash
# 1. 執行 composer 產出 latest.json
python3 scripts/composer.py

# 2. 讀取並格式化輸出
python3 scripts/deepear_lite.py --local

# 3. 驗證 JSON 結構
python3 tests/test_composer.py
```
