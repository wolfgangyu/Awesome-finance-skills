# Skill Cleanup: Remove BERT and A-Share Dependencies

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip BERT/transformers sentiment code and akshare A-share/HK-share stock code from alphaear-search, alphaear-reporter, and alphaear-signal-tracker.

**Architecture:**
- `alphaear-search` is the simplest (flat `scripts/` layout), so it serves as the template.
- `alphaear-reporter` and `alphaear-signal-tracker` share the same nested `scripts/utils/` layout and nearly identical utility files. Changes applied to one can be mirrored to the other.
- `sentiment_tools.py` follows the same pattern already applied to `alphaear-sentiment`: remove BERT pipeline, `analyze_sentiment`, `analyze_sentiment_bert`; keep only `update_single_news_sentiment` and `batch_update_news_sentiment` (no-op).
- `stock_tools.py` in reporter and tracker is deleted entirely — both skills' SKILL.md already say to delegate stock queries to `alphaear-stock`.
- `database_manager.py` removes `stock_prices` table/methods. `stock_list` stays in signal-tracker because `fin_agent.py` calls `get_stock_by_code()`.

**Tech Stack:** Python 3.10+, sqlite3, loguru

## Global Constraints

- No akshare imports anywhere in the repo.
- No BERT/transformers sentiment code in any skill.
- `sentiment_tools.py` keeps only `update_single_news_sentiment` and `batch_update_news_sentiment` (signature-compatible with `alphaear-sentiment`).
- `database_manager.py` in reporter and tracker removes `stock_prices` table and `save_stock_prices`/`get_stock_prices` methods.
- `stock_list` and `get_stock_by_code` stay in signal-tracker (used by `fin_agent.py`).
- All import references to deleted code must be cleaned up.

---

## Task 1: Clean up alphaear-search sentiment_tools.py

**Files:**
- Modify: `skills/alphaear-search/scripts/sentiment_tools.py`
- Modify: `skills/alphaear-search/scripts/search_tools.py`

**Interfaces:**
- Consumes: Existing BERT-laden `SentimentTools`
- Produces: Agent-only `SentimentTools` with `update_single_news_sentiment` and `batch_update_news_sentiment`

- [ ] **Step 1: Write new sentiment_tools.py**

```python
import os
from typing import Dict, List, Union, Optional
import json
from loguru import logger
from .database_manager import DatabaseManager


class SentimentTools:
    """
    情緒分析工具 — 由 Agent 自行判斷情緒分數。

    此工具提供資料庫存取功能，實際的情緒分析由呼叫端的 Agent 執行。
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    def update_single_news_sentiment(self, news_id: Union[str, int], score: float, reason: str = "") -> bool:
        """將 Agent 分析的情緒結果保存到資料庫。"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                UPDATE daily_news
                SET sentiment_score = ?, meta_data = json_set(COALESCE(meta_data, '{}'), '$.sentiment_reason', ?)
                WHERE id = ?
            """, (score, reason, news_id))
            self.db.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update sentiment for {news_id}: {e}")
            return False

    def batch_update_news_sentiment(self, source: Optional[str] = None, limit: int = 50) -> int:
        """批量更新資料庫中新聞的情緒分數 — 由 Agent 自行執行分析。"""
        news_items = self.db.get_daily_news(source=source, limit=limit)
        to_analyze = [item for item in news_items if not item.get('sentiment_score')]
        if not to_analyze:
            return 0
        logger.info(f"📝 {len(to_analyze)} unanalyzed news items found. Agent should perform sentiment analysis and call update_single_news_sentiment for each.")
        return 0
```

- [ ] **Step 2: Fix search_tools.py import**

In `skills/alphaear-search/scripts/search_tools.py`, find the lazy import block around line 386:

Old:
```python
from .sentiment_tools import SentimentTools
```

This import stays valid — no change needed since `SentimentTools` still exists. But the call to `analyze_sentiment` will now return error. That's fine — the enrichment block gracefully degrades.

- [ ] **Step 3: Verify tests pass**

```bash
# Check import doesn't fail
python3 -c "
import sys
sys.path.insert(0, 'skills/alphaear-search')
from scripts.sentiment_tools import SentimentTools
from scripts.database_manager import DatabaseManager
db = DatabaseManager(':memory:')
t = SentimentTools(db)
print('OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add skills/alphaear-search/scripts/sentiment_tools.py
git commit -m "refactor(search): strip BERT from sentiment_tools, delegate to Agent"
```

---

## Task 2: Clean up alphaear-reporter (sentiment + stock + DB)

**Files:**
- Modify: `skills/alphaear-reporter/scripts/utils/sentiment_tools.py`
- Delete: `skills/alphaear-reporter/scripts/utils/stock_tools.py`
- Modify: `skills/alphaear-reporter/scripts/utils/database_manager.py`
- Modify: `skills/alphaear-reporter/scripts/tools/toolkits.py`

**Interfaces:**
- Consumes: sentiment_tools with BERT, stock_tools with akshare, database_manager with stock tables
- Produces: Agent-only sentiment_tools, no stock_tools, clean database_manager

- [ ] **Step 1: Strip sentiment_tools.py**

Replace `skills/alphaear-reporter/scripts/utils/sentiment_tools.py` with the same Agent-only version from Task 1.

- [ ] **Step 2: Delete stock_tools.py**

```bash
rm skills/alphaear-reporter/scripts/utils/stock_tools.py
```

- [ ] **Step 3: Clean database_manager.py**

Remove `stock_prices` table creation (the `CREATE TABLE IF NOT EXISTS stock_prices` block, typically ~6 lines).
Remove `stock_list` table creation block.
Remove methods: `save_stock_list`, `search_stock`, `get_stock_by_code`, `save_stock_prices`, `get_stock_prices`.

Check if `import pandas as pd` is still needed after removal — if only used by stock methods, remove it.

- [ ] **Step 4: Remove StockToolkit from toolkits.py**

In `skills/alphaear-reporter/scripts/tools/toolkits.py`:
- Remove `from ..utils.stock_tools import StockTools` import
- Remove the `StockToolkit` class (likely ~100 lines)

- [ ] **Step 5: Fix search_tools.py import path**

In `skills/alphaear-reporter/scripts/utils/search_tools.py`, find:
```python
from ..sentiment_tools import SentimentTools
```
Change to:
```python
from .sentiment_tools import SentimentTools
```
(Since search_tools.py is inside `utils/`, and sentiment_tools.py is also in `utils/`, the correct relative import is `.sentiment_tools`.)

- [ ] **Step 6: Verify**

```bash
python3 -c "
import sys
sys.path.insert(0, 'skills/alphaear-reporter')
from scripts.utils.sentiment_tools import SentimentTools
from scripts.utils.database_manager import DatabaseManager
db = DatabaseManager(':memory:')
t = SentimentTools(db)
print('OK')
"
```

- [ ] **Step 7: Commit**

```bash
git add skills/alphaear-reporter/scripts/utils/sentiment_tools.py \
        skills/alphaear-reporter/scripts/utils/database_manager.py \
        skills/alphaear-reporter/scripts/tools/toolkits.py
git rm skills/alphaear-reporter/scripts/utils/stock_tools.py
git commit -m "refactor(reporter): strip BERT, remove akshare stock_tools, clean DB"
```

---

## Task 3: Clean up alphaear-signal-tracker (sentiment + stock + DB)

**Files:**
- Modify: `skills/alphaear-signal-tracker/scripts/utils/sentiment_tools.py`
- Delete: `skills/alphaear-signal-tracker/scripts/utils/stock_tools.py`
- Modify: `skills/alphaear-signal-tracker/scripts/utils/database_manager.py`
- Modify: `skills/alphaear-signal-tracker/scripts/tools/toolkits.py`

**Interfaces:**
- Consumes: Same as reporter (BERT sentiment, akshare stock, bloated DB)
- Produces: Same as reporter BUT keeps `stock_list` table + `get_stock_by_code()` for `fin_agent.py`

- [ ] **Step 1: Strip sentiment_tools.py**

Same as Task 1/2 — replace with Agent-only version.

- [ ] **Step 2: Delete stock_tools.py**

```bash
rm skills/alphaear-signal-tracker/scripts/utils/stock_tools.py
```

- [ ] **Step 3: Clean database_manager.py (partial)**

Remove `stock_prices` table creation block.
Remove methods: `save_stock_list`, `search_stock`, `save_stock_prices`, `get_stock_prices`.

**KEEP**: `stock_list` table and `get_stock_by_code()` — `fin_agent.py` line 84 calls `self.db.get_stock_by_code(code)` for ticker validation.

Check if `import pandas as pd` is needed — only `save_stock_prices` and `get_stock_prices` used it. Remove if unused.

- [ ] **Step 4: Remove StockToolkit from toolkits.py**

Same as Task 2 Step 4 — remove import and `StockToolkit` class.

- [ ] **Step 5: Fix search_tools.py import path**

Same as Task 2 Step 5: `from ..sentiment_tools` → `from .sentiment_tools`.

- [ ] **Step 6: Verify**

```bash
python3 -c "
import sys
sys.path.insert(0, 'skills/alphaear-signal-tracker')
from scripts.utils.sentiment_tools import SentimentTools
from scripts.utils.database_manager import DatabaseManager
db = DatabaseManager(':memory:')
t = SentimentTools(db)
# Verify get_stock_by_code still works
stock = db.get_stock_by_code('2330')
print('OK')
"
```

- [ ] **Step 7: Commit**

```bash
git add skills/alphaear-signal-tracker/scripts/utils/sentiment_tools.py \
        skills/alphaear-signal-tracker/scripts/utils/database_manager.py \
        skills/alphaear-signal-tracker/scripts/tools/toolkits.py
git rm skills/alphaear-signal-tracker/scripts/utils/stock_tools.py
git commit -m "refactor(signal-tracker): strip BERT, remove akshare stock_tools, clean DB"
```

---

## Task 4: Final verification

**Files:**
- None (verification only)

- [ ] **Step 1: Confirm no akshare imports remain**

```bash
grep -r "import akshare" skills/ || echo "Clean"
grep -r "akshare" skills/ || echo "Clean"
```

- [ ] **Step 2: Confirm no BERT sentiment pipelines remain**

```bash
grep -r "bert_pipeline" skills/ || echo "Clean"
grep -r "AutoTokenizer" skills/ || echo "Clean"
grep -r "from transformers" skills/ || echo "Clean"
```

- [ ] **Step 3: Run all existing smoke tests**

```bash
python3 -m unittest tests.alphaear-sentiment.test_sentiment -v
python3 -m unittest tests.alphaear-stock.test_stock -v
```

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: verify no akshare/BERT dependencies remain" --allow-empty
```