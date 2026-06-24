# AlphaEar Schema Consolidation & Market Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate duplicated Pydantic schemas into a shared package, remove A-share/HK-share support, add Taiwan stock support, and convert all user-facing text to Traditional Chinese (Taiwan).

**Architecture:**
- **Schema consolidation**: Extract shared Pydantic models into `skills/_shared/alphaear_schema/`, vendor into each skill via sync script.
- **Market refactor**: Remove `akshare` and `EastMoneyDirect` dependencies, implement `TWSEClient` for Taiwan stocks, retain `yfinance` for US stocks.
- **Traditional Chinese conversion**: Convert all user-facing text (SKILL.md, README.md, docstrings, log/error messages) to zh-TW using `tools/convert_zh_tw.py`.

**Tech Stack:** Python 3.10+, Pydantic v2, pandas, requests, yfinance, SQLite

## Global Constraints

- **Schema consolidation**: Single source of truth in `skills/_shared/alphaear_schema/`, vendored into each skill via `tools/sync_shared_schema.py`.
- **Market refactor**: Remove all `akshare` and `EastMoneyDirect` code; support only US (yfinance) and Taiwan (TWSE/TPEx) stocks.
- **Traditional Chinese conversion**: All user-facing text must use Taiwan vocabulary (e.g., "訊號" → "訊號", "軟體" → "軟體").
- **Backward compatibility**: Deprecation shim for `scripts/schema/models.py` until v1.2.0.
- **Testing**: Each task must include a failing test before implementation.

---

## Phase 1: Schema Consolidation

### Task 1.1: Create Shared Schema Package

**Files:**
- Create: `skills/_shared/alphaear_schema/__init__.py`
- Create: `skills/_shared/alphaear_schema/models.py`
- Create: `skills/_shared/alphaear_schema/isq_template.py`
- Create: `skills/_shared/alphaear_schema/__vendored__.py`

**Interfaces:**
- Consumes: `skills/alphaear-predictor/scripts/schema/models.py` (base schema)
- Produces: `InvestmentSignal`, `TransmissionNode`, `KLinePoint`, `ForecastResult`, `ResearchContext`, `ScanContext`, `SignalCluster`, `ClusterContext`, `IntentAnalysis`, `FilterResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_shared_schema.py
def test_shared_schema_round_trip():
    from alphaear_schema import InvestmentSignal
    signal = InvestmentSignal(
        signal_id="test_sig",
        title="Test Signal",
        summary="Test Summary",
        reasoning="Test Reasoning",
        transmission_chain=[],
        sentiment_score=0.5,
        confidence=0.8,
        intensity=3,
        expectation_gap=0.2,
        timeliness=0.9,
        expected_horizon="T+1",
        price_in_status="未知",
        impact_tickers=[],
        industry_tags=[],
        sources=[]
    )
    assert signal.model_dump(mode="json") == {
        "signal_id": "test_sig",
        "title": "Test Signal",
        "summary": "Test Summary",
        "reasoning": "Test Reasoning",
        "transmission_chain": [],
        "sentiment_score": 0.5,
        "confidence": 0.8,
        "intensity": 3,
        "expectation_gap": 0.2,
        "timeliness": 0.9,
        "expected_horizon": "T+1",
        "price_in_status": "未知",
        "impact_tickers": [],
        "industry_tags": [],
        "sources": []
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_shared_schema.py::test_shared_schema_round_trip -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'alphaear_schema'"
```

- [ ] **Step 3: Write minimal implementation**

```python
# skills/_shared/alphaear_schema/__init__.py
from .models import *
__version__ = "1.1.0"

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
    summary: str = "暂无摘要分析"
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
    old_field: Optional[str] = Field(default=None, deprecated=True)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_shared_schema.py::test_shared_schema_round_trip -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/_shared/alphaear_schema/ tests/test_shared_schema.py
git commit -m "feat(schema): create shared alphaear_schema package"
```

---

### Task 1.2: Implement Sync Script

**Files:**
- Create: `tools/sync_shared_schema.py`
- Test: `tests/test_sync_shared_schema.py`

**Interfaces:**
- Consumes: `skills/_shared/alphaear_schema/`
- Produces: `sync_shared_schema.py` CLI (`--check`, `--help`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sync_shared_schema.py
def test_sync_script_check_mode():
    import subprocess
    result = subprocess.run(
        ["python", "tools/sync_shared_schema.py", "--check"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "No drift detected" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_sync_shared_schema.py::test_sync_script_check_mode -v
# Expected: FAIL with "FileNotFoundError: [Errno 2] No such file or directory: 'tools/sync_shared_schema.py'"
```

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
Sync shared alphaear_schema to all skills.
"""

import shutil
import subprocess
import sys
from pathlib import Path

def get_version():
    """Get version from _shared/__init__.py"""
    init_path = Path("skills/_shared/alphaear_schema/__init__.py")
    for line in init_path.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split("=")[1].strip().strip("\"'")
    return "0.0.0"

def sync_skill(skill_path: Path):
    """Sync schema to one skill"""
    shared_src = Path("skills/_shared/alphaear_schema")
    vendor_dst = skill_path / "scripts/alphaear_schema"
    shim_path = skill_path / "scripts/schema/models.py"
    
    # Copy shared schema to vendor dir
    shutil.copytree(shared_src, vendor_dst, dirs_exist_ok=True)
    
    # Write version stamp
    (vendor_dst / "__vendored__.py").write_text(
        f"__version__ = '{get_version()}'\n"
        f"__commit__ = '{subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()}'\n"
    )
    
    # Add deprecation shim
    shim_path.write_text(
        "# DEPRECATED: 請改用 `scripts.alphaear_schema`\n"
        "from scripts.alphaear_schema.models import *  # noqa: F401,F403\n"
    )

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check for drift")
    args = parser.parse_args()
    
    if args.check:
        print("Checking for drift...")
        # Check that all vendored copies match _shared
        shared_src = Path("skills/_shared/alphaear_schema")
        for skill in ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]:
            vendor_dst = Path(f"skills/{skill}/scripts/alphaear_schema")
            if not vendor_dst.exists():
                print(f"ERROR: {vendor_dst} does not exist")
                sys.exit(1)
            # Compare __vendored__.py version
            shared_version = None
            for line in (shared_src / "__init__.py").read_text().splitlines():
                if line.startswith("__version__"):
                    shared_version = line.split("=")[1].strip().strip("\"'")
                    break
            vendor_version = None
            for line in (vendor_dst / "__vendored__.py").read_text().splitlines():
                if line.startswith("__version__"):
                    vendor_version = line.split("=")[1].strip().strip("\"'")
                    break
            if shared_version != vendor_version:
                print(f"ERROR: {vendor_dst} version {vendor_version} != {shared_version}")
                sys.exit(1)
        print("No drift detected")
        return
    
    for skill in ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]:
        sync_skill(Path(f"skills/{skill}"))
    print("Sync complete")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
chmod +x tools/sync_shared_schema.py
pytest tests/test_sync_shared_schema.py::test_sync_script_check_mode -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add tools/sync_shared_schema.py tests/test_sync_shared_schema.py
git commit -m "feat(schema): implement sync_shared_schema.py"
```

---

### Task 1.3: Vendor Schema into Skills

**Files:**
- Modify: `skills/alphaear-predictor/scripts/schema/models.py` (deprecation shim)
- Modify: `skills/alphaear-reporter/scripts/schema/models.py` (deprecation shim)
- Modify: `skills/alphaear-signal-tracker/scripts/schema/models.py` (deprecation shim)
- Create: `skills/alphaear-predictor/scripts/alphaear_schema/` (vendored)
- Create: `skills/alphaear-reporter/scripts/alphaear_schema/` (vendored)
- Create: `skills/alphaear-signal-tracker/scripts/alphaear_schema/` (vendored)

**Interfaces:**
- Consumes: `tools/sync_shared_schema.py`
- Produces: Vendored `alphaear_schema/` in each skill

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema_consistency.py
import os
from pathlib import Path

def test_vendored_schema_exists():
    skills = ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]
    for skill in skills:
        vendor = Path(f"skills/{skill}/scripts/alphaear_schema")
        assert vendor.exists(), f"{vendor} missing"
        assert (vendor / "models.py").exists(), f"{vendor}/models.py missing"
        assert (vendor / "__init__.py").exists(), f"{vendor}/__init__.py missing"

def test_vendored_versions_match():
    import re
    src_version = None
    for line in Path("skills/_shared/alphaear_schema/__init__.py").read_text().splitlines():
        if line.startswith("__version__"):
            src_version = line.split("=")[1].strip().strip("\"'")
            break
    assert src_version is not None
    for skill in ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]:
        stamp = (Path(f"skills/{skill}/scripts/alphaear_schema/__vendored__.py")
                 .read_text())
        assert src_version in stamp
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_schema_consistency.py -v
# Expected: FAIL (vendored schema does not exist yet)
```

- [ ] **Step 3: Run sync script**

```bash
python tools/sync_shared_schema.py
```

- [ ] **Step 4: Verify vendored copies**

```bash
ls -la skills/*/scripts/alphaear_schema/__vendored__.py
# Expected: 3 files, each with __version__ and __commit__
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/scripts/alphaear_schema/ skills/*/scripts/schema/models.py
git commit -m "feat(schema): vendor alphaear_schema into all skills"
```

---

### Task 1.4: Update SKILL.md Dependencies

**Files:**
- Modify: `skills/alphaear-predictor/SKILL.md`
- Modify: `skills/alphaear-reporter/SKILL.md`
- Modify: `skills/alphaear-signal-tracker/SKILL.md`

**Interfaces:**
- Consumes: Vendored `alphaear_schema/`
- Produces: Updated `SKILL.md` dependencies

- [ ] **Step 1: Write the failing test**

```python
# tests/test_skill_md.py
def test_skill_md_dependencies():
    for skill in ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]:
        md = Path(f"skills/{skill}/SKILL.md").read_text()
        assert "alphaear_schema" in md
        assert "vendored" in md
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_skill_md.py::test_skill_md_dependencies -v
# Expected: FAIL (no alphaear_schema mention)
```

- [ ] **Step 3: Update SKILL.md**

```markdown
## Dependencies

- `alphaear_schema` (vendored, version=`1.1.0`)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_skill_md.py::test_skill_md_dependencies -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/SKILL.md
git commit -m "docs: update SKILL.md dependencies for alphaear_schema"
```

---

## Phase 2: Market Refactor

### Task 2.1: Remove A-share/HK-share Code

**Files:**
- Modify: `skills/alphaear-stock/scripts/stock_tools.py` (remove `akshare`, `EastMoneyDirect`)
- Modify: `skills/alphaear-predictor/scripts/utils/stock_tools.py` (remove `akshare`)
- Modify: `skills/alphaear-reporter/scripts/utils/stock_tools.py` (remove `akshare`)
- Modify: `skills/alphaear-signal-tracker/scripts/utils/stock_tools.py` (remove `akshare`)
- Modify: `skills/alphaear-stock/SKILL.md` (remove `akshare` dependency)

**Interfaces:**
- Consumes: `akshare` and `EastMoneyDirect` code
- Produces: Stock tools that support only US and Taiwan stocks

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stock_tools.py
def test_stock_tools_no_akshare():
    import subprocess
    # Check that akshare is not imported
    result = subprocess.run(
        ["grep", "-r", "import akshare", "skills/"],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0  # grep returns 1 if no matches
    assert "akshare" not in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_stock_tools.py::test_stock_tools_no_akshare -v
# Expected: FAIL (akshare imports still present)
```

- [ ] **Step 3: Remove akshare/EastMoneyDirect**

```python
# Example: skills/alphaear-stock/scripts/stock_tools.py
# Remove: import akshare, EastMoneyDirect class, all akshare/EastMoney calls
# Keep: yfinance, TWSEClient (to be implemented in Task 2.2)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_stock_tools.py::test_stock_tools_no_akshare -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/scripts/*stock_tools.py skills/alphaear-stock/SKILL.md
git commit -m "refactor(market): remove akshare and EastMoneyDirect code"
```

---

### Task 2.2: Implement TWSEClient

**Files:**
- Create: `skills/alphaear-stock/scripts/twse_client.py`
- Test: `tests/test_twse_client.py`

**Interfaces:**
- Consumes: TWSE/TPEx HTTP endpoints
- Produces: `TWSEClient.fetch_kline()` returning `pd.DataFrame`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_twse_client.py
def test_twse_client_fetch_kline():
    from scripts.twse_client import TWSEClient
    df = TWSEClient.fetch_kline("2330", "2026-06-01", "2026-06-22")
    assert not df.empty
    assert "date" in df.columns
    assert "open" in df.columns
    assert "close" in df.columns
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_twse_client.py::test_twse_client_fetch_kline -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'scripts.twse_client'"
```

- [ ] **Step 3: Write minimal implementation**

```python
# skills/alphaear-stock/scripts/twse_client.py
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
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        return df
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_twse_client.py::test_twse_client_fetch_kline -v
# Expected: PASS (or FAIL with network error, but interface is correct)
```

- [ ] **Step 5: Commit**

```bash
git add skills/alphaear-stock/scripts/twse_client.py tests/test_twse_client.py
git commit -m "feat(market): implement TWSEClient for Taiwan stocks"
```

---

### Task 2.3: Update StockTools for US/TW Support

**Files:**
- Modify: `skills/alphaear-stock/scripts/stock_tools.py`
- Modify: `skills/alphaear-predictor/scripts/utils/stock_tools.py`
- Modify: `skills/alphaear-reporter/scripts/utils/stock_tools.py`
- Modify: `skills/alphaear-signal-tracker/scripts/utils/stock_tools.py`
- Test: `tests/test_stock_tools.py`

**Interfaces:**
- Consumes: `yfinance`, `TWSEClient`
- Produces: `search_ticker()`, `get_stock_price()`, `get_stock_fundamentals()` supporting US/TW tickers

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stock_tools.py
def test_stock_tools_us_tw_support():
    from scripts.stock_tools import StockTools
    from utils.database_manager import DatabaseManager
    
    db = DatabaseManager(":memory:")
    tools = StockTools(db)
    
    # Test US ticker
    df_us = tools.get_stock_price("AAPL", "2026-06-01", "2026-06-22")
    assert not df_us.empty
    
    # Test TW ticker
    df_tw = tools.get_stock_price("2330", "2026-06-01", "2026-06-22")
    assert not df_tw.empty
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_stock_tools.py::test_stock_tools_us_tw_support -v
# Expected: FAIL (TWSEClient not integrated)
```

- [ ] **Step 3: Update StockTools**

```python
# Example: skills/alphaear-stock/scripts/stock_tools.py
import yfinance as yf
from .twse_client import TWSEClient

def get_stock_price(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    clean_ticker = "".join(filter(str.isdigit, ticker))
    
    if len(clean_ticker) == 4:  # TW ticker
        df = TWSEClient.fetch_kline(clean_ticker, start_date, end_date)
    else:  # US ticker
        df = yf.download(ticker, start=start_date, end=end_date)
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
    
    return df
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_stock_tools.py::test_stock_tools_us_tw_support -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/scripts/*stock_tools.py
git commit -m "feat(market): update StockTools for US/TW support"
```

---

### Task 2.4: Remove A-share/HK-share DB Tables

**Files:**
- Modify: `skills/alphaear-stock/scripts/database_manager.py`
- Modify: `skills/alphaear-predictor/scripts/utils/database_manager.py`
- Modify: `skills/alphaear-reporter/scripts/utils/database_manager.py`
- Modify: `skills/alphaear-signal-tracker/scripts/utils/database_manager.py`

**Interfaces:**
- Consumes: `stock_list` table (A-share/HK-share entries)
- Produces: Cleaned DB schema

- [ ] **Step 1: Write the failing test**

```python
# tests/test_database_manager.py
def test_database_manager_no_ashare():
    from utils.database_manager import DatabaseManager
    db = DatabaseManager(":memory:")
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_list'")
    tables = cursor.fetchall()
    # stock_list should exist, but should not contain A-share/HK-share entries
    cursor.execute("SELECT COUNT(*) FROM stock_list WHERE code LIKE '6%' OR code LIKE '0%' OR code LIKE '116.%'")
    count = cursor.fetchone()[0]
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_database_manager.py::test_database_manager_no_ashare -v
# Expected: FAIL (A-share/HK-share entries still present)
```

- [ ] **Step 3: Clean DB schema**

```python
# Example: skills/alphaear-stock/scripts/database_manager.py
# In _init_db(), remove stock_list table creation if not needed
# Or, keep stock_list but ensure it only contains US/TW tickers
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_database_manager.py::test_database_manager_no_ashare -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/scripts/*database_manager.py
git commit -m "refactor(market): remove A-share/HK-share DB tables"
```

---

### Task 2.5: Update SKILL.md Market Support

**Files:**
- Modify: `skills/alphaear-stock/SKILL.md`
- Modify: `skills/alphaear-predictor/SKILL.md`
- Modify: `skills/alphaear-reporter/SKILL.md`
- Modify: `skills/alphaear-signal-tracker/SKILL.md`

**Interfaces:**
- Consumes: Updated market support
- Produces: Updated `SKILL.md` market section

- [ ] **Step 1: Write the failing test**

```python
# tests/test_skill_md.py
def test_skill_md_market_support():
    for skill in ["alphaear-stock", "alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]:
        md = Path(f"skills/{skill}/SKILL.md").read_text()
        assert "US stocks" in md
        assert "Taiwan stocks" in md
        assert "A-share" not in md
        assert "HK-share" not in md
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_skill_md.py::test_skill_md_market_support -v
# Expected: FAIL (A-share/HK-share still mentioned)
```

- [ ] **Step 3: Update SKILL.md**

```markdown
## Supported Markets

- **US stocks**: via `yfinance`
- **Taiwan stocks**: via TWSE/TPEx official HTTP endpoints
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_skill_md.py::test_skill_md_market_support -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/SKILL.md
git commit -m "docs: update SKILL.md market support"
```

---

## Phase 3: Traditional Chinese Conversion

### Task 3.1: Implement Conversion Tool

**Files:**
- Create: `tools/convert_zh_tw.py`
- Create: `tools/check_zh_tw.py`
- Test: `tests/test_zh_tw.py`

**Interfaces:**
- Consumes: Simplified Chinese text
- Produces: Traditional Chinese (Taiwan) text

- [ ] **Step 1: Write the failing test**

```python
# tests/test_zh_tw.py
def test_convert_zh_tw():
    from tools.convert_zh_tw import convert_zh_tw
    text = "訊號 軟體 網路 下載 本機"
    converted = convert_zh_tw(text)
    assert converted == "訊號 軟體 網路 下載 本機"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_zh_tw.py::test_convert_zh_tw -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'tools.convert_zh_tw'"
```

- [ ] **Step 3: Write minimal implementation**

```python
# tools/convert_zh_tw.py
import re

ZH_TW_MAP = {
    "訊號": "訊號",
    "軟體": "軟體",
    "網路": "網路",
    "下載": "下載",
    "本機": "本機",
    "东方财富": "東方財富",
    "代號": "代號",
    "記憶體": "記憶體",
    "重新取得": "重新取得",
    "證券": "證券",
    "交易所": "交易所",
    "市值": "市值",
    "本益比": "本益比",
    "成交量": "成交量",
    "漲跌幅": "漲跌幅",
    "振幅": "振幅",
    "換手率": "換手率",
    "日期": "日期",
    "開盤": "開盤",
    "收盤": "收盤",
    "最高": "最高",
    "最低": "最低",
    "成交額": "成交額",
    "漲跌額": "漲跌額",
}

def convert_zh_tw(text: str) -> str:
    for sc, tc in ZH_TW_MAP.items():
        text = text.replace(sc, tc)
    return text

# tools/check_zh_tw.py
import re
import sys
from pathlib import Path

def check_zh_tw(path: str):
    sc_pattern = re.compile(r"[一-鿿]")
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if sc_pattern.search(line):
            print(f"Simplified Chinese found in {path}: {line}")
            return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_zh_tw.py::test_convert_zh_tw -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add tools/convert_zh_tw.py tools/check_zh_tw.py tests/test_zh_tw.py
git commit -m "feat(i18n): implement convert_zh_tw.py and check_zh_tw.py"
```

---

### Task 3.2: Convert SKILL.md and README.md

**Files:**
- Modify: `skills/*/SKILL.md`
- Modify: `README.md`
- Modify: `skills/*/references/*.md`

**Interfaces:**
- Consumes: Simplified Chinese text
- Produces: Traditional Chinese (Taiwan) text

- [ ] **Step 1: Write the failing test**

```python
# tests/test_zh_tw.py
def test_skill_md_zh_tw():
    from tools.check_zh_tw import check_zh_tw
    for skill in ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker", "alphaear-stock"]:
        assert check_zh_tw(f"skills/{skill}/SKILL.md")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_zh_tw.py::test_skill_md_zh_tw -v
# Expected: FAIL (Simplified Chinese found)
```

- [ ] **Step 3: Convert files**

```bash
python tools/convert_zh_tw.py --path skills/*/SKILL.md README.md skills/*/references/*.md
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_zh_tw.py::test_skill_md_zh_tw -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/SKILL.md README.md skills/*/references/*.md
git commit -m "feat(i18n): convert SKILL.md and README.md to Traditional Chinese"
```

---

### Task 3.3: Convert Python Docstrings and Log Messages

**Files:**
- Modify: `skills/*/scripts/*.py` (docstrings, log/error messages)

**Interfaces:**
- Consumes: Simplified Chinese docstrings/logs
- Produces: Traditional Chinese (Taiwan) docstrings/logs

- [ ] **Step 1: Write the failing test**

```python
# tests/test_zh_tw.py
def test_python_docstrings_zh_tw():
    from tools.check_zh_tw import check_zh_tw
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "[一-鿿]", "skills/*/scripts/*.py"],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0  # grep returns 1 if no matches
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_zh_tw.py::test_python_docstrings_zh_tw -v
# Expected: FAIL (Simplified Chinese found)
```

- [ ] **Step 3: Convert docstrings/logs**

```bash
python tools/convert_zh_tw.py --path skills/*/scripts/*.py
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_zh_tw.py::test_python_docstrings_zh_tw -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/*/scripts/*.py
git commit -m "feat(i18n): convert Python docstrings and log messages to Traditional Chinese"
```

---

### Task 3.4: Update README for zh-TW Support

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Updated zh-TW support
- Produces: Updated `README.md` language section

- [ ] **Step 1: Write the failing test**

```python
# tests/test_readme.py
def test_readme_zh_tw_support():
    readme = Path("README.md").read_text()
    assert "Traditional Chinese (Taiwan)" in readme
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_readme.py::test_readme_zh_tw_support -v
# Expected: FAIL (no zh-TW mention)
```

- [ ] **Step 3: Update README.md**

```markdown
## Language Support

- All user-facing text is in **Traditional Chinese (Taiwan)**.
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_readme.py::test_readme_zh_tw_support -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: update README.md for Traditional Chinese support"
```