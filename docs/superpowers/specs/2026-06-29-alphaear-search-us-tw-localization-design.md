# alphaear-search 美台股本地化支援設計

- **日期：** 2026-06-29
- **狀態：** 已核准
- **關聯技能：** alphaear-search
- **作者：** Claude Code + Wolfgang

## 背景

alphaear-search 目前支援 4 個搜尋引擎（Jina、DuckDuckGo、百度、本地 RAG），但缺乏針對美股與台股的地域化支援。程式碼中存在大量簡體中文註解，且沒有自動偵測市場類型或取得即時股價的功能。

## 目標

1. 將所有簡體中文註解轉換為繁體中文
2. 新增 Google 搜尋引擎（透過 Jina Reader 包裝）
3. 自動偵測搜尋查詢的市場類型（美股 / 台股）
4. 根據市場類型選擇最適搜尋引擎
5. 在搜尋結果中整合即時股價（透過 yfinance）
6. 使用 humanize-zh 套件格式化日期、數字、貨幣
7. 新增單元測試驗證市場偵測與引擎選擇邏輯

## 非目標

- 不修改現有搜尋引擎的核心邏輯（Jina、DDG、百度）
- 不引入新的 LLM 模型或提示模板
- 不改變現有資料庫結構
- 不涉及其他市場（日股、韓股等）

## 設計方案

### 1. 搜尋引擎擴充

#### 新增 `scripts/google_search_engine.py`

仿照現有的 `JinaSearchEngine` 結構，使用 Jina Reader 包裝 Google 搜尋：

```
GET https://s.jina.ai/Google+查詢
```

回傳格式與其他引擎一致（`List[Dict]`），包含 `title`、`url`、`content`。

#### 修改 `scripts/search_tools.py`

在 `_engines` 字典新增 `"google": GoogleSearchEngine()`。

### 2. 市場偵測邏輯

```python
import re

# 美股 ticker：2-5 個大寫字母（AAPL, MSFT, NVDA, AI 等）
US_TICKER_RE = re.compile(r'\b[A-Z]{2,5}\b')

# 台股代號：4 碼數字（2330, 2454, 3231 等）
TW_TICKER_RE = re.compile(r'\b\d{4}\b')

# 台股公司名稱關鍵字
TW_KEYWORDS = ['台積電', '聯發科', '鴻海', '台達電', '富邦金', '兆豐金']

# 美股公司名稱關鍵字
US_KEYWORDS = ['蘋果', '英偉達', '微軟', '特斯拉', '谷歌', '亞馬遜', 'Meta']
```

**偵測優先級：**

1. 檢查是否包含台股代號（4 碼數字）→ `tw`
2. 檢查是否包含台股公司名稱 → `tw`
3. 檢查是否包含美股 ticker（大寫字母）→ `us`
4. 檢查是否包含美股公司名稱 → `us`
5. 無法判斷 → `None`（使用預設邏輯）

### 3. 引擎選擇規則

| 市場 | 優先引擎 | 備援引擎 | 搜尋語言 |
|------|---------|---------|---------|
| 美股 (`us`) | `jina` | `ddg` | 英文 |
| 台股 (`tw`) | `google` | `ddg` | 繁體中文 |
| 未知 (`None`) | 現有預設邏輯 | 現有備援 | 保持原樣 |

### 4. 即時股價整合

新增 `_enrich_with_price(results, market)` 方法：

- 從搜尋結果中提取 ticker 符號
- 使用 `yfinance` 查詢即時股價
- 美股：`ticker`（如 `AAPL`）
- 台股：`ticker.TW`（如 `2330.TW`）
- 結果追加欄位：`price`, `currency`, `change`, `change_pct`, `source`

**錯誤處理：**

- yfinance 查詢失敗 → 記錄 warning，略過該筆股價，不影響主流程
- 無有效 ticker 可查詢 → 跳過股價 enrich

### 5. humanize-zh 整合

新增 `scripts/utils/humanize.py`：

- 安裝自 [wolfgangyu/lab-drawer](https://github.com/wolfgangyu/lab-drawer/tree/main/humanizer)
- 用於：
  - 日期格式化：`2024-01-15T10:30:00` → `3 小時前` / `昨天`
  - 數字格式化：`1234567` → `123.4 萬` / `1.2M`
  - 貨幣格式化：`USD 150.5` → `$150.5 美元`
- 搜尋結果中的時間戳記、價格、成交量等欄位使用 humanize 格式化

### 6. 繁簡轉換

**涉及檔案清單：**

- `SKILL.md` — 全文繁體中文化
- `scripts/search_tools.py` — 註解繁體中文化
- `scripts/database_manager.py` — 註解繁體中文化
- `scripts/hybrid_search.py` — 註解繁體中文化
- `scripts/content_extractor.py` — 註解繁體中文化
- `scripts/sentiment_tools.py` — 註解繁體中文化
- `scripts/llm/router.py` — 註解繁體中文化
- `scripts/llm/factory.py` — 註解繁體中文化
- `scripts/llm/capability.py` — 註解繁體中文化
- `references/PROMPTS.md` — 繁體中文化

**轉換規則：**

- 使用專案現有的 `tools/convert_zh_tw.py` 工具
- 保留專業術語英文不翻譯（如 API, ticker, engine）
- 符合台北中文排版習慣（中英文之間加空格）

### 7. 測試策略

#### `tests/alphaear-search/test_market_detection.py`

測試 `_detect_market()` 方法：

- 台股代號：`"2330"` → `"tw"`
- 美股 ticker：`"AAPL"` → `"us"`
- 台股公司名：`"台積電"` → `"tw"`
- 美股公司名：`"英偉達"` → `"us"`
- 混合查詢：`"NVDA 財報"` → `"us"`
- 無法判斷：`"最新新聞"` → `None`

#### `tests/alphaear-search/test_engine_selection.py`

測試 `_select_engine()` 方法：

- `us` → `jina`
- `tw` → `google`
- `None` → 預設引擎

#### `tests/alphaear-search/test_price_enrichment.py`

模擬 yfinance 回傳，驗證 `_enrich_with_price()`：

- 美股 ticker enrich 正確
- 台股 ticker.TW enrich 正確
- yfinance 失敗時不中斷主流程

## 檔案變更摘要

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `scripts/google_search_engine.py` | 新增 | Google 搜尋引擎（Jina Reader 包裝） |
| `scripts/search_tools.py` | 修改 | 新增市場偵測、引擎選擇、股價 enrich |
| `scripts/utils/__init__.py` | 新增 | utils 套件初始化 |
| `scripts/utils/humanize.py` | 新增 | humanize-zh 整合 |
| `tests/alphaear-search/test_market_detection.py` | 新增 | 市場偵測測試 |
| `tests/alphaear-search/test_engine_selection.py` | 新增 | 引擎選擇測試 |
| `tests/alphaear-search/test_price_enrichment.py` | 新增 | 股價 enrich 測試 |
| 所有 `.py` 檔案 | 修改 | 繁簡轉換（簡體 → 繁體） |
| `SKILL.md` | 修改 | 全文繁體中文化 |
| `references/PROMPTS.md` | 修改 | 繁體中文化 |

## 依賴變更

| 套件 | 用途 | 來源 |
|------|------|------|
| `yfinance` | 即時股價查詢 | PyPI（應已有） |
| `humanize-zh` | 繁體中文人性化格式化 | [wolfgangyu/lab-drawer](https://github.com/wolfgangyu/lab-drawer/tree/main/humanizer) |

## 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| humanize-zh 安裝失敗 | 格式化功能無法使用 | 使用內建格式化替代，不影響主流程 |
| yfinance 連線失敗 | 股價 enrich 失敗 | 記錄 warning，略過該筆股價 |
| Google 搜尋引擎失敗 | 台股搜尋品質下降 | 降級至 DDG |
| 市場偵測誤判 | 引擎選擇錯誤 | 允許使用者手動指定 market 參數 |
