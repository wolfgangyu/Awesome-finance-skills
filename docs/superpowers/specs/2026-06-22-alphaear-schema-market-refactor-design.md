# AlphaEar Schema Consolidation & Market Refactor Design

**Date**: 2026-06-22
**Author**: Wolfgang Yu
**Status**: Draft (awaiting review)

## 1. Context

### 1.1. Schema Consolidation

Three skills (`alphaear-predictor`, `alphaear-reporter`, `alphaear-signal-tracker`) each maintain their own copy of Pydantic schemas:

- `InvestmentSignal`, `TransmissionNode`, `KLinePoint`, `ForecastResult`, `ResearchContext`, `ScanContext`, `SignalCluster`, `ClusterContext`, `IntentAnalysis`, `FilterResult`
- These schemas are **95% identical** across skills, leading to:
  - **Maintenance drift**: bug fixes or new fields must be manually synced to three places.
  - **Version skew**: downstream consumers (e.g., DeepEar) may receive different schema versions depending on which skill they install.
  - **Testing overhead**: smoke tests must validate three copies of the same contract.

### 1.2. Market Refactor

Current `alphaear-stock` skill supports:

- **A-share** (via `akshare` + `EastMoneyDirect` fallback)
- **HK-share** (via `akshare` + `EastMoneyDirect` fallback)
- **US stocks** (via `yfinance`)

**Goals**:
- **Remove A-share/HK-share support**: drop `akshare` and `EastMoneyDirect` dependencies.
- **Add Taiwan stock support**: use TWSE/TPEx official HTTP endpoints.
- **Keep US stocks**: retain `yfinance` (no proxy fallback needed).

### 1.3. Traditional Chinese (zh-TW) Conversion

All user-facing text (SKILL.md, README, reference/*.md, scripts docstrings, log/error messages) is currently in Simplified Chinese. **Goal**: convert to **Taiwan Traditional Chinese** (詞彙基準：臺灣口語，例：股票→股市、代碼→代號、記憶體、網路、重新取得、訊號、下載、本機、戇件、訊息、頻變識)。

## 2. Architecture

### 2.1. Schema Consolidation

```
Awesome-finance-skills/
├── skills/
│   ├── _shared/
│   │   └── alphaear_schema/          # ← Single source of truth (Python package)
│   │       ├── __init__.py           #   exports all models
│   │       ├── models.py            #   InvestmentSignal, KLinePoint, ...
│   │       ├── isq_template.py      #   DEFAULT_ISQ_TEMPLATE
│   │       └── __vendored__.py      #   version stamp (written by sync script)
│   └── <skill>/
│       ├── scripts/
│       │   └── alphaear_schema/      # ← Vendored copy (managed by sync script)
│       │       ├── __init__.py       #   re-exports from _shared
│       │       ├── models.py
│       │       ├── isq_template.py
│       │       └── __vendored__.py
│       └── SKILL.md
├── tools/
│   └── sync_shared_schema.py       # ← One-way sync: _shared → skills
```

### 2.2. Market Refactor

```
skills/alphaear-stock/scripts/
├── stock_tools.py
│   ├── StockTools
│   │   ├── search_ticker()           # → TWSE/TPEx + yfinance
│   │   ├── get_stock_price()        # → TWSE/TPEx + yfinance
│   │   └── get_stock_fundamentals() # → TWSE/TPEx + yfinance
│   └── TWSEClient                  # ← New: Taiwan stock HTTP client
└── database_manager.py             # ← Remove A-share/HK-share tables
```

### 2.3. Traditional Chinese Conversion

- **Scope**: SKILL.md, README.md, reference/*.md, scripts docstrings, log/error messages.
- **Tool**: `tools/convert_zh_tw.py` (uses OpenCC `s2twp.json` + custom overrides).
- **Validation**: `tools/check_zh_tw.py` (grep for leftover Simplified Chinese).

## 3. Schema Consolidation

### 3.1. Base Schema (alphaear-predictor)

The following models are **fully consolidated** into `alphaear_schema/models.py`:

| Model | Fields | Notes |
|:------|:-------|:------|
| `InvestmentSignal` | `signal_id`, `title`, `summary`, `reasoning`, `transmission_chain`, `sentiment_score`, `confidence`, `intensity`, `expectation_gap`, `timeliness`, `expected_horizon`, `price_in_status`, `impact_tickers`, `industry_tags`, `sources` | Core signal model |
| `TransmissionNode` | `node_name`, `impact_type`, `logic` | Chain node |
| `KLinePoint` | `date`, `open`, `high`, `low`, `close`, `volume` | OHLCV data |
| `ForecastResult` | `ticker`, `base_forecast`, `adjusted_forecast`, `rationale`, `timestamp` | Forecast container |
| `ResearchContext` | `raw_signal`, `tickers_found`, `industry_background`, `latest_developments`, `key_risks`, `search_results_summary` | Research data |
| `ScanContext` | `hot_topics`, `news_summaries`, `market_data`, `sentiment_overview`, `raw_data_summary` | Scan data |
| `SignalCluster` | `theme_title`, `signal_ids`, `rationale` | Cluster metadata |
| `ClusterContext` | `clusters` | Cluster container |
| `IntentAnalysis` | `keywords`, `search_queries`, `is_specific_event`, `time_range`, `intent_summary` | Intent data |
| `FilterResult` | `has_valid_signals`, `selected_ids`, `themes`, `reason` | Filter result |

### 3.2. Skill-Specific Extensions

| Skill | Extension | Handling |
|:------|:----------|:---------|
| `alphaear-predictor` | `Evaluation`, `Training` (in `utils/predictor/`) | **Not consolidated** (predictor-only training infra) |
| `alphaear-reporter` | `InvestmentReport` (extends `InvestmentSignal`) | **Consolidated** into `alphaear_schema/models.py` with `extra="allow"` |
| `alphaear-signal-tracker` | None | Fully consolidated |

### 3.3. Deprecation Handling

- **Backward compatibility**: Fields that are being phased out are marked with `Field(..., deprecated=True)`.
- **Validation**: Pydantic v2 automatically emits `DeprecationWarning` on use.
- **Serialization**: `model_dump(mode="json")` includes deprecated fields by default (configurable).

## 4. Market Refactor

### 4.1. Removed Support

| Market | Dependency | Action |
|:-------|:-----------|:-------|
| A-share | `akshare`, `EastMoneyDirect` | Remove all code, deps, and DB tables |
| HK-share | `akshare`, `EastMoneyDirect` | Remove all code, deps, and DB tables |

### 4.2. Retained Support

| Market | Dependency | Notes |
|:-------|:-----------|:------|
| US stocks | `yfinance` | No changes |

### 4.3. Added Support

| Market | Source | Endpoint |
|:-------|:-------|:---------|
| Taiwan stocks | TWSE/TPEx official HTTP | `https://www.twse.com.tw/exchangeReport/STOCK_DAY` (TWSE)<br>`https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/stock_day.php` (TPEx) |

### 4.4. New Client: `TWSEClient`

```python
class TWSEClient:
    """台灣證交所 / 櫃買中心官方 HTTP 客戶端。"""
    
    TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    TPEX_URL = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/stock_day.php"
    
    @classmethod
    def fetch_kline(cls, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """取得台灣股市 K 線資料。"""
        # ...
```

### 4.5. Updated `StockTools`

```python
class StockTools:
    def search_ticker(self, query: str, limit: int = 5) -> List[Dict]:
        """模糊搜尋台灣/美國股票代號或名稱。"""
        # ...
    
    def get_stock_price(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """取得台灣/美國股票歷史價格。"""
        # ...
    
    def get_stock_fundamentals(self, ticker: str) -> Dict:
        """取得公司基本面資料（市值、產業、本益比等）。"""
        # ...
```

## 5. Traditional Chinese Conversion

### 5.1. Scope

| File Type | Action |
|:----------|:-------|
| SKILL.md | Convert to zh-TW |
| README.md | Convert to zh-TW |
| reference/*.md | Convert to zh-TW |
| scripts/*.py (docstrings) | Convert to zh-TW |
| scripts/*.py (log/error messages) | Convert to zh-TW |
| scripts/*.py (code) | No change |

### 5.2. Tooling

```bash
# Convert Simplified Chinese to Traditional Chinese (Taiwan)
python tools/convert_zh_tw.py

# Check for leftover Simplified Chinese
python tools/check_zh_tw.py
```

### 5.3. Vocabulary Mapping

| Simplified | Traditional (Taiwan) |
|:------------|:----------------------|
| 股票 | 股市 |
| 代码 | 代號 |
| 记忆 | 記憶體 |
| 网络 | 網路 |
| 重新获取 | 重新取得 |
| 信号 | 訊號 |
| 下载 | 下載 |
| 本地 | 本機 |
| 软件 | 軟體 |
| 消息 | 訊息 |
| 频变识 | 頻變識 |
| 证券 | 證券 |
| 交易所 | 交易所 |
| 市值 | 市值 |
| 本益比 | 本益比 |
| 成交量 | 成交量 |
| 涨跌幅 | 漲跌幅 |
| 振幅 | 振幅 |
| 换手率 | 換手率 |
| 日期 | 日期 |
| 开盘 | 開盤 |
| 收盘 | 收盤 |
| 最高 | 最高 |
| 最低 | 最低 |
| 成交额 | 成交額 |
| 涨跌额 | 漲跌額 |

## 6. Deprecation Shim

### 6.1. Purpose

- Allow existing imports (`from scripts.schema.models import InvestmentSignal`) to continue working during the deprecation period.
- Provide a clear migration path to the new import path (`from scripts.alphaear_schema import InvestmentSignal`).

### 6.2. Implementation

In each skill's `scripts/schema/models.py`:

```python
# DEPRECATED: 請改用 `from scripts.alphaear_schema import InvestmentSignal`
from scripts.alphaear_schema.models import *  # noqa: F401,F403
```

### 6.3. Timeline

| Version | Action | Impact |
|:--------|:-------|:-------|
| **v1.1.0** | Add shim | Both import paths work |
| **v1.1.1–v1.1.x** | Maintain shim | Backward compatible |
| **v1.2.0** | Remove shim | `from scripts.schema.models` raises `ImportError` |

## 7. Testing

### 7.1. Schema Consistency

- **Test**: `tests/test_shared_schema.py`
  - Import `from alphaear_schema import InvestmentSignal`.
  - Validate round-trip JSON serialization.
  - Ensure deprecated fields are ignored in `model_dump(exclude_deprecated=True)`.

- **Test**: `tests/test_schema_consistency.py`
  - Assert all vendored copies have the same `__version__`.
  - Assert no manual edits to vendored directories (hash mismatch).

### 7.2. Market Refactor

- **Test**: `tests/test_stock_tools.py`
  - `search_ticker()`: returns TWSE/TPEx + yfinance results.
  - `get_stock_price()`: returns TWSE/TPEx + yfinance data.
  - `get_stock_fundamentals()`: returns TWSE/TPEx + yfinance data.
  - **Negative test**: A-share/HK-share tickers return empty DataFrame.

- **Test**: `tests/test_twse_client.py`
  - `TWSEClient.fetch_kline()`: returns valid DataFrame for TWSE/TPEx tickers.

### 7.3. Traditional Chinese Conversion

- **Test**: `tests/test_zh_tw.py`
  - Assert no Simplified Chinese in SKILL.md, README.md, reference/*.md.
  - Assert no Simplified Chinese in scripts docstrings/log messages.

## 8. Rollout Plan

### 8.1. Phase 1: Schema Consolidation (v1.1.0)

1. Create `skills/_shared/alphaear_schema/` and populate with consolidated schemas.
2. Implement `tools/sync_shared_schema.py`.
3. Run sync script to vendor schemas into all three skills.
4. Add deprecation shim to `scripts/schema/models.py`.
5. Update SKILL.md dependencies to note the vendored schema.
6. Add pre-commit hook for `sync_shared_schema.py --check`.

### 8.2. Phase 2: Market Refactor (v1.1.0)

1. Remove `akshare` and `EastMoneyDirect` dependencies.
2. Implement `TWSEClient` for Taiwan stock data.
3. Update `StockTools` to use TWSE/TPEx + yfinance.
4. Remove A-share/HK-share DB tables.
5. Update SKILL.md to reflect supported markets.

### 8.3. Phase 3: Traditional Chinese Conversion (v1.1.0)

1. Implement `tools/convert_zh_tw.py` and `tools/check_zh_tw.py`.
2. Convert all user-facing text to zh-TW.
3. Validate with `tools/check_zh_tw.py`.
4. Update README to note zh-TW support.

### 8.4. Phase 4: Maintenance (v1.1.1–v1.1.x)

- All schema changes **must** go through `_shared/alphaear_schema/`.
- Run sync script after every change.
- Monitor downstream consumers for migration progress.

### 8.5. Phase 5: Cleanup (v1.2.0)

1. Remove deprecation shim (`scripts/schema/models.py`).
2. Update all internal imports to use `scripts.alphaear_schema`.
3. Update tests to use the new import path.
4. Update README to reflect the new import path.

## 9. Out of Scope

- **Prompts**: Shared prompt strings (e.g., `references/PROMPTS.md`) are not consolidated in this spec.
- **Toolkits**: Shared utility classes (e.g., `scripts/utils/toolkits.py`) are not consolidated.
- **Training infrastructure**: Predictor-specific training/evaluation code remains in `alphaear-predictor`.
- **Database schemas**: Each skill's `DatabaseManager` remains independent.

## 10. Risks and Mitigations

| Risk | Mitigation |
|:-----|:-----------|
| Vendored copies drift from source | Pre-commit hook enforces sync; CI fails on drift |
| Downstream consumers ignore deprecation | Clear timeline in README; CHANGELOG entry for v1.2.0 |
| Schema changes break downstream | Semantic versioning; deprecation warnings before removal |
| Sync script fails mid-transaction | Atomic writes (tmp dir + rename) |
| TWSE/TPEx API changes | Fallback to cached data; log warning |
| Traditional Chinese conversion errors | `tools/check_zh_tw.py` validation; manual review |

## 11. Appendix

### 11.1. Example: InvestmentSignal

```python
# skills/_shared/alphaear_schema/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class TransmissionNode(BaseModel):
    node_name: str
    impact_type: str
    logic: str

class InvestmentSignal(BaseModel):
    signal_id: str = "unknown_sig"
    title: str
    summary: str = "暫無摘要分析"
    reasoning: str = ""
    transmission_chain: List[TransmissionNode] = []
    sentiment_score: float = 0.0
    confidence: float = 0.5
    intensity: int = 3
    expectation_gap: float = 0.5
    timeliness: float = 0.8
    expected_horizon: str = "T+N"
    price_in_status: str = "未知"
    impact_tickers: List[Dict] = []
    industry_tags: List[str] = []
    sources: List[Dict] = []
    # Deprecated fields
    old_field: Optional[str] = Field(default=None, deprecated=True)
```

### 11.2. Sync Script Pseudocode

```python
import shutil
from pathlib import Path

def sync_skill(skill_path: Path):
    shared_src = Path("skills/_shared/alphaear_schema")
    vendor_dst = skill_path / "scripts/alphaear_schema"
    shim_path = skill_path / "scripts/schema/models.py"
    
    # Copy shared schema to vendor dir
    shutil.copytree(shared_src, vendor_dst, dirs_exist_ok=True)
    
    # Write version stamp
    with open(vendor_dst / "__vendored__.py", "w") as f:
        f.write(f"__version__ = '{get_version()}'\n")
    
    # Add deprecation shim
    with open(shim_path, "w") as f:
        f.write("# DEPRECATED: 請改用 `scripts.alphaear_schema`\n")
        f.write("from scripts.alphaear_schema.models import *  # noqa\n")
```

### 11.3. TWSEClient Example

```python
import pandas as pd
import requests

class TWSEClient:
    TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    TPEX_URL = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/stock_day.php"
    
    @classmethod
    def fetch_kline(cls, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """取得台灣股市 K 線資料。"""
        params = {
            "response": "json",
            "date": end_date.replace("-", ""),
            "stockNo": ticker,
        }
        resp = requests.get(cls.TWSE_URL, params=params)
        data = resp.json()
        if not data.get("data"):
            return pd.DataFrame()
        
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df = df.rename(columns={
            "日期": "date",
            "開盤價": "open",
            "最高價": "high",
            "最低價": "low",
            "收盤價": "close",
            "成交股數": "volume",
        })
        return df
```