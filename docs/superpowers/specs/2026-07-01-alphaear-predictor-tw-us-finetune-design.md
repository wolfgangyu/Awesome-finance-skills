# alphaear-predictor 美台股 news_proj 訓練適配設計

- **日期：** 2026-07-01
- **狀態：** 已核准
- **關聯技能：** alphaear-predictor
- **作者：** Claude Code + Wolfgang

## 背景

alphaear-predictor 目前使用 Kronos 基礎模型（via `KronosPredictorUtility`）進行 K 線時間序列預測，並透過 `news_proj` 投射層整合新聞情感。現有訓練流程（`scripts/utils/predictor/training.py::AutoSynthesisTrainer`）存在以下限制：

1. **新聞搜尋引擎綁定百度**：搜尋引擎固定使用 `BaiduSearchTools`（`scripts/utils/search_tools.py:168`），對美股與台股（非簡中語境）無法取得有效新聞。
2. **市場偵測不完整**：`training.py:111` 呼叫 `db.get_stock_by_code(shock['ticker'])` 取得公司名稱，但資料庫僅含台股資料，美股 ticker 會回傳空值。
3. **無交易日曆支援**：`kronos_predictor.py:132` 使用 `pd.date_range(..., freq='B')` 推算未來日期，不認識 TWSE / NYSE 假日。
4. **訓練不可重跑**：無 cache 機制，每次執行 `python -m training.py` 需重新搜尋新聞（含 LLM 因果驗證），耗時且浪費 API token。
5. **shock 門檻一刀切**：`threshold=2.0`（`training.py:75`）對台股合理，對美股大盤股偏高，對加密貨幣偏低。

此設計聚焦在 **Scope A**：只擴充現有 news_proj 訓練流程，不引入上游 `finetune_csv` 全模型微調路線。

## 決策摘要

| # | 決定 | 備註 |
|---|------|------|
| 1 | Scope：只擴充 news_proj 訓練，不引入上游 finetune_csv | 凍結主體路線 |
| 2 | 禁用百度搜尋引擎 | 台股改用 yfinance news + CNA RSS；美股改用 yfinance news + Google News RSS |
| 3 | lookback=20, pred_len=5（日 K） | 沿用現有 SKILL.md 預設 |
| 4 | 離線先收集新聞（含 cache）+ 訓練可重跑 | 三階段 CLI（collect / train / evaluate） |
| 5 | 新 .pt 覆蓋既有 `kronos_news_v1_*.pt` | 覆蓋前備份一份到 `exports/models/_backup/` |
| 6 | Unverified shocks 保留進訓練 | 標記 `causality="unverified"`，評估時分組輸出 MAE |
| 7 | 歷史不足 / 無 shock 的 ticker 寫入 `skipped_tickers.json` | build_dataset 結束時印 summary |

## 非目標

- 不引入上游 `finetune_csv` 全模型微調路線（留待後續 Scope B）
- 不修改現有 `KronosPredictorUtility.get_base_forecast()` 的推理介面（SKILL.md 第 21 行）
- 不改變 `scripts/kronos_predictor.py` 的推理路徑
- 不引入新 Python 套件（pandas_market_calendars 除外）
- 不修改現有 `scripts/utils/search_tools.py` 的搜尋入口（新增 `news_sources.py` 獨立包裝）
- 不涉及其他市場（日股、韓股等）

## 設計方案

### 1. 檔案結構變更

```
skills/alphaear-predictor/
├── SKILL.md                                      # 微調說明補上「TW / US market-aware training」
├── scripts/
│   ├── build_dataset.py                 # 新增：Stage 1 資料蒐集 entry
│   ├── train_news_proj.py               # 新增：Stage 2 訓練 entry
│   ├── evaluate_news_proj.py            # 新增：Stage 3 評估 entry（從 evaluation.py 重構）
│   ├── utils/
│   │   ├── market_detect.py             # 新增：ticker 市場分類 + 名稱解析
│   │   ├── news_sources.py              # 新增：依市場分流的新聞來源
│   │   ├── trading_calendar.py          # 新增：TWSE / NYSE 交易日曆
│   │   └── predictor/
│   │       ├── training.py              # 瘦身為共用 helper（AutoSynthesisTrainer 保留 core）
│   │       └── evaluation.py            # 瘦身為共用 helper（NewsModelEvaluator 保留 core）
│   └── tests/test_*.py                  # 新增對應的 smoke 測試
└── exports/
    ├── models/
    │   ├── kronos_news_<timestamp>.pt   # 訓練產出
    │   ├── kronos_news_latest.txt       # 指向最新 .pt 檔名的純文字 placeholder
    │   └── _backup/                     # 覆蓋前的舊 .pt 備份（.gitignore）
    └── training_results/                # 既有評估輸出目錄（保留）
```

### 2. `market_detect.py` — 市場分類與名稱解析

#### 2.1 `detect_market(ticker: str) -> Literal["TW", "US", "OTHER", "CRYPTO"]`

**判定規則：**

| 規則 | 範例 | 結果 |
|------|------|------|
| 4 碼數字且首位不為 0 | `2330` | `TW` |
| `.TW` 副檔名 | `2330.TW` | `TW` |
| 全大寫英文字母 ≤ 5 碼 | `AAPL` | `US` |
| `BTC-USD` / `BTC/USDT` | `BTC-USD` | `CRYPTO` |
| 其他 | `XYZ123` | `OTHER` |

**優先級：** TW > US > CRYPTO > OTHER

#### 2.2 `resolve_name(ticker: str, market: str) -> str`

| 市場 | 來源 | 備援 |
|------|------|------|
| TW | `db.get_stock_by_code(ticker)['name']` | ticker 本身 |
| US | `yf.Ticker(ticker).info['longName']` | ticker 本身 |
| CRYPTO | ticker 本身 | — |
| OTHER | ticker 本身 | — |

### 3. `news_sources.py` — 依市場分流的新聞來源

#### 3.1 核心類別

```python
class NewsItem(TypedDict):
    title: str
    url: str
    body: str
    published_at: str

class MarketAwareNewsSource:
    def collect(self, ticker: str, market: str, shock_date: str) -> List[NewsItem]
```

#### 3.2 市場分流規則

| 市場 | 來源 | 查詢方式 |
|------|------|----------|
| TW | 1. `yf.Ticker(ticker + ".TW").news`<br>2. CNA RSS (`feeds.feedburner.com/rsscna/finance`) | ticker 名稱 + 日期 contains 搜尋 |
| US | 1. `yf.Ticker(ticker).news`<br>2. Google News RSS | ticker + date en-US |

#### 3.3 硬約束

- **禁止使用百度搜尋引擎**：`news_sources.py` 頂端加入 `assert "baidu" not in Path(__file__).read_text()` 在 CI 驗證。
- 重複呼叫同一 `(ticker, market, shock_date)` → 走既有 `search_cache` 表（`query_hash = sha256(f"{market}|{ticker}|{shock_date}")`）。

### 4. `trading_calendar.py` — 依市場算下一個交易日

```python
def next_trading_day(market: str, after: pd.Timestamp, n: int = 1) -> pd.DatetimeIndex
```

- 預設先用 `pandas.tseries.offsets.BusinessDay()`（沿用現有 `kronos_predictor.py:132` 行為）。
- 未來可擴充為 TWSE / NYSE 公開假日 JSON 快取。

### 5. `build_dataset.py` — Stage 1 資料蒐集

#### 5.1 CLI

```bash
python scripts/build_dataset.py \
    --tickers auto --from 2024-01-01 --to 2026-06-30 \
    --shock-threshold 2.0 --markets TW,US --max-per-stock 5
```

#### 5.2 流程

```
discover_shocks() → collect_news() → verify_causality() → write_parquet()
```

1. **discover_shocks**：讀 `stock_tools.get_stock_price`，偵測 `change_pct.abs() > threshold` 的 shock。
2. **collect_news**：依 `market_detect.detect_market(ticker)` 分流，寫入 `search_cache`。
3. **verify_causality**：LLM 因果驗證（改寫 prompt 為英文/中文依市場）。
4. **寫出 parquet**：`data/training_dataset.parquet`

#### 5.3 Parquet Schema

```
[
  { ticker, market, shock_date,
    history_rows: List[Dict],     # open/high/low/close/volume/date
    target_rows:  List[Dict],
    news_text:    str,
    news_emb:      List[float],    # 384 維，由 embedder.encode(news_text[:1000]) 事先算好
    causality:    Literal["verified", "unverified"],
    unverified_reason: Optional[str]  # "llm_rejected" / "no_news" / "llm_parse" / "llm_unavailable"
  }
]
```

#### 5.4 Cache 層

| 層 | Key | 機制 |
|----|-----|------|
| search_cache | `sha256(market\|ticker\|shock_date)` | 既有 `db.get_search_cache` |
| RSS 快取 | RSS URL | `data/news_rss_cache.json`，12h TTL |
| LLM 因果驗證 | `sha256(ticker + date + first_news_url)` | `data/causality_cache.parquet` |
| news_emb | `sha256(news_text)` | `data/news_emb_cache.parquet` |

#### 5.5 Skipped Tickers

所有跳過的 ticker 寫入 `data/skipped_tickers.json`：

```json
[
  {"code": "2330", "reason": "insufficient_history_45days"},
  {"code": "AAPL", "reason": "no_shock_in_range"}
]
```

CLI 結束時印 summary：

```
=== Build Dataset Summary ===
Total tickers scanned: 100
Successfully processed: 85
Skipped: 15
  - insufficient_history: 8
  - no_shock_in_range: 5
  - unsupported_market: 2
Shocks discovered: 342
  - with news: 280
  - without news: 62
Verified by LLM: 210
Unverified (kept): 70
Parquet written: data/training_dataset.parquet (280 rows)
```

### 6. `train_news_proj.py` — Stage 2 訓練

#### 6.1 CLI

```bash
python scripts/train_news_proj.py \
    --dataset data/training_dataset.parquet \
    --epochs 30 --lr 1e-3 --seed 42 \
    [--resume exports/models/kronos_news_v1_20260101_0015.pt]
    [--out-name kronos_news_v2]
```

#### 6.2 流程

1. 讀 parquet → DataFrame
2. 載入 Kronos + Tokenizer（凍結所有參數：`model.requires_grad_(False)`）
3. 載入既有 `.pt`（若指定 `--resume` → warm start；若無 → news_proj 隨機初始化）
4. **訓練 loop**（同 `training.py:249-293` 邏輯）：
   - `optimizer = Adam(model.news_proj.parameters(), lr=1e-3)`
   - `teacher forcing on s1_targets`
   - 主體全程 `no_grad`
   - **不過濾 unverified 樣本**（全部加入訓練）
5. **備份與儲存**：
   - 寫出新 `.pt` 到 `exports/models/kronos_news_<timestamp>.pt`
   - 覆蓋前將舊檔備份到 `exports/models/_backup/`（此目錄需加入 `.gitignore`）
   - 寫一份 `exports/models/kronos_news_latest.txt`，內容為最新 .pt 的檔名（**Windows 友善，不使用 symlink**）
6. 輸出 `training_report.json`：loss 曲線、best loss、train/val 樣本數、config 快照

#### 6.3 Reproducibility

- `torch.manual_seed(seed)` + `torch.backends.cudnn.deterministic = True`
- `--dry` 模式：跑 forward 不更新 weights，用於驗證 pipe

### 7. `evaluate_news_proj.py` — Stage 3 評估

#### 7.1 CLI

```bash
python scripts/evaluate_news_proj.py \
    --model exports/models/kronos_news_latest.pt \
    [--us-only] [--tw-only] [--pred-len 5]
```

1. 載入最新 `.pt`（沿用 `glob.glob('kronos_news_*.pt')` max ctime）
2. 從 `stock_list` 抓 US tickers（或 TW，依 flag）
3. `discover_shocks(test_tickers, pred_len=5)`
4. 對每個 shock：base vs news-aware predict，MAE%（相對 close）
5. 輸出 summary 到 console + `exports/training_results/eval_<timestamp>.html`
6. **分組輸出**：`verified` vs `unverified` 兩組 MAE 對比

#### 7.2 Console 格式

```
========================================================================================
Date         | Ticker   | Base MAE       | News MAE       | Improvement
----------------------------------------------------------------------------------------
2024-01-15   | AAPL     | 0.5234         | 0.4891         |   +6.5%
2024-03-22   | 2330     | 1.2345         | 1.1234         |   +9.0%
========================================================================================
AVERAGE      | -        | 0.8790         | 0.8063         |   +8.2%
========================================================================================
```

### 8. 錯誤處理策略

#### 8.1 資料層

| 情境 | 行為 | 記錄 |
|------|------|------|
| `detect_market(ticker) → OTHER/CRYPTO` | 跳過 | `skipped_tickers.json` 加 `{"code": ..., "reason": "unsupported_market"}` |
| `get_stock_price` 回 empty | 跳過 | `skipped_tickers.json` 加 `{"code": ..., "reason": "no_history"}` |
| 歷史 < 60 天 | 跳過 | `skipped_tickers.json` 加 `{"code": ..., "reason": "insufficient_history_<n>days"}` |
| 找不到 shock | 跳過 | `skipped_tickers.json` 加 `{"code": ..., "reason": "no_shock_in_range"}` |
| news 全空 | 加進 dataset，`causality="unverified"`, `unverified_reason="no_news"` | — |
| LLM 回傳非 JSON | 加進，標 `unverified_reason="llm_parse"` | — |
| LLM 超時 / 5xx | retry 3 次（exp backoff 1/2/4s），仍失敗 → unverified / "llm_unavailable" | — |
| LLM `is_causal=false` | 加進，標 `unverified_reason="llm_rejected"` | — |
| parquet 寫出中途 crash | atomic write：先寫 `*.tmp` 再 rename | — |

#### 8.2 模型層

| 情境 | 行為 |
|------|------|
| Kronos base 從 HF 下載失敗 | 印「請手動放到 `~/.cache/huggingface/hub/`」並 exit code 2 |
| `kronos_news_*.pt` glob 沒檔案 | 繼續訓練，news_proj 從隨機初始化 |
| `.pt` 載入失敗（key/state 不匹配） | 回 legacy load；legacy 也炸 → 整體退出並請使用者手動檢查 |
| 訓練中 OOM | 保留截至 OOM 前的 best checkpoint（不覆蓋既有 v1） |
| GPU 不可用 | 退回 CPU，並 warning |

#### 8.3 IO / 路徑層

| 情境 | 行為 |
|------|------|
| `exports/models/` 不存在 | `os.makedirs(..., exist_ok=True)` |
| `--resume` 但找不到來源 .pt | CLI 報錯 exit code 3 |
| `latest` 同步 | Windows 預設使用 `kronos_news_latest.txt` placeholder（內容為最新 .pt 檔名），不嘗試 symlink |
| `data/news_emb_cache.parquet` 損壞 | 印 warning 跳過，用 in-memory recount |

### 9. 測試策略

#### 9.1 原則

- 遵循 CLAUDE.md 測試慣例：tests 為「**import + 初始化 smoke**」，不強求 LLM/Kronos 真的跑起來。
- 新測試必須是「可在無 GPU、無 HF token、無 LLM API key 下跑通」。
- CI 必跑；本地 heavy 測試（真的 load Kronos、真的 fetch yfinance）標 `@pytest.mark.heavy`，預設 skip。

#### 9.2 測試檔案清單

```
tests/alphaear-predictor/
├── test_market_detect.py          # 純函式測試，不需要 IO
├── test_news_sources.py           # mock search_cache 與 HTTP fetch
├── test_trading_calendar.py       # TW/US 已知假日樣本比對
├── test_build_dataset.py          # mock StockTools / NewsSource / LLM
├── test_train_news_proj.py        # mock Kronos 與 parquet，提供 tiny fixture
├── test_evaluate_news_proj.py     # mock .pt、mock shocks
└── test_predictor.py              # 既有，確認 import path 不被新檔破壞
```

#### 9.3 關鍵斷言

**test_market_detect.py**（純函式）
- `detect_market("2330") == "TW"`
- `detect_market("AAPL") == "US"`
- `detect_market("BTC-USD") == "CRYPTO"`
- `detect_market("XYZ123") == "OTHER"`
- `resolve_name("2330", "TW")` 不為空、為 str
- 不需要 DB（內部若需要在 fixture 注入 dummy db stub）

**test_news_sources.py**
- monkeypatch `db.get_search_cache` 回既有的 cache → collect 直接回 cached，沒打外網
- monkeypatch yfinance `Ticker(t).news` 回 fake
- mock RSS XML：用 `responses` 套件攔截 feed URL
- **`test_no_baidu`**：`Path.read_text()` 對 `news_sources.py` 全文 grep，**必須沒有 'baidu' 這個字串**

**test_trading_calendar.py**
- `next_trading_day("US", pd.Timestamp("2025-07-03")) == [2025-07-07]`（繞開 7/4 獨立紀念日）
- `next_trading_day("TW", ...)` 對應某已知國定假日（如雙十）略過
- 對既有 `pandas.tseries.offsets.BusinessDay` 行為作 cross-check

**test_build_dataset.py**
- 注入 fake `StockTools.get_stock_price` 回固定 90 行 df（含 1 個 shock）
- mock news + LLM：`build_dataset.run(["FAKE1"], ...)` 必須產出 parquet
- 對 LLM 回 invalid JSON 走 retry → 仍成功
- **對 unverified 樣本，確保沒被過濾掉**

**test_train_news_proj.py**
- 提供 `data/fixture_dataset.parquet`（5 筆樣本），跑 1 epoch
- 斷言：訓練後 `model.news_proj.weight` 改變了一點（gradient ≠ 0）
- 斷言：訓練後 `model.embedding.weight` 完全不變（主體凍結）
- 斷言：結束後 `exports/models/kronos_news_<timestamp>.pt` 存在

**test_evaluate_news_proj.py**
- mock glob.max ctime → 固定 .pt
- 對 fixed shocks 跑 base vs news-aware，產出 console 表格 + html 路徑存在
- 斷言 summary 包含 "AVERAGE" 那行（沿用既有格式）

#### 9.4 Fixture 與資料控管

- 不在 tests 目錄放真實 OHLCV parquet（避免被 commit）。
- 提供 `tests/fixtures/mini_kline_60d.csv`（5-8 筆人工生成的小資料）
- `conftest.py` 提供 `tmp_data_dir` autouse fixture，自動 monkey-patch `data/` 到 tmp 處理 parquet 與 cache

## 實施順序建議

1. **Phase 1**：`market_detect.py` + `news_sources.py` + `trading_calendar.py`（純 util，可獨立測試）
2. **Phase 2**：`build_dataset.py`（Stage 1 整合）
3. **Phase 3**：`train_news_proj.py`（Stage 2 整合）
4. **Phase 4**：`evaluate_news_proj.py`（Stage 3 整合）
5. **Phase 5**：測試 + SKILL.md 更新

## Hard Constraints（未來 Proposal 必須討論怎麼解）

1. **禁百度**：`news_sources.py` 不得出現 `baidu` 關鍵字
2. **不引入新依賴**（`pandas_market_calendars` 除外）
3. **news_proj-only 凍結主體**：不碰上游 `finetune_csv` 全模型微調
4. **預設 lookback=20 pred_len=5**：日 K 為主
5. **TW / US 限定**：不涉及其他市場（日股、韓股等）
6. **Windows 相容**：不使用 symlink；`kronos_news_latest.txt` 為預設同步機制

7. **不修改現有 `KronosPredictorUtility.get_base_forecast()` 的推理介面**
