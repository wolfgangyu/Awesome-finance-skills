# Task 2: ReportGenerator 核心邏輯

**專案脈絡**：
本任務實作 alphaear-reporter 的核心邏輯抽象化，將現有的 Agentic Workflow 轉換為可程式化呼叫的 `ReportGenerator` 類別。這是統一設計的核心元件，將被 CLI、Python API 和 Agentic Workflow 三種進入點共用。

**檔案**：
- Create: `skills/alphaear-reporter/scripts/report_generator.py`
- Test: `tests/test_reporter.py`

**介面定義**：
```python
from typing import List, Dict, Any, Optional
from loguru import logger
from .utils.database_manager import DatabaseManager
from .utils.llm.base_client import LLMClient  # Task 1 實作

class ReportGenerator:
    def __init__(
        self,
        db: DatabaseManager,
        llm_client: Optional[LLMClient] = None,
        market: str = "tw",
    ):
        self.db = db
        self.llm_client = llm_client
        self.market = market

    async def generate_report(
        self,
        signals: List[Dict[str, Any]],
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """生成完整報告"""
        logger.info(f"開始生成報告，訊號數量：{len(signals)}")
        return {
            "markdown": "",
            "json": {},
            "line_friendly": "",
        }
```

**核心方法實作**：
1. `_cluster_signals`: 將訊號聚類成主題簇
2. `_write_section`: 撰寫單個章節
3. `_assemble_report`: 組裝完整報告
4. `_parse_to_json`: 將 Markdown 解析為結構化 JSON
5. `_simplify_for_line`: 將報告簡化為 LINE 官方帳號友好格式

**簡化邏輯（無 LLM 模式）**：
```python
async def _cluster_signals(
    self,
    signals: List[Dict[str, Any]],
    use_llm: bool = True,
) -> List[Dict[str, Any]]:
    """將訊號聚類成主題簇"""
    if not use_llm or not self.llm_client:
        # 簡化邏輯：按 ticker 聚類
        clusters = {}
        for signal in signals:
            ticker = signal.get("ticker", "unknown")
            if ticker not in clusters:
                clusters[ticker] = {
                    "ticker": ticker,
                    "signals": [],
                    "title": f"{ticker} 相關訊號",
                }
            clusters[ticker]["signals"].append(signal)
        return list(clusters.values())
```

**測試**：
```python
import pytest
from skills.alphaear-reporter.scripts.report_generator import ReportGenerator
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager

@pytest.fixture
def mock_signals():
    return [
        {"title": "台積電營收創新高", "content": "台積電公布 7 月營收...", "ticker": "2330.TW"},
        {"title": "AI 需求推動半導體", "content": "NVIDIA 新一代 GPU...", "ticker": "2330.TW"},
    ]

def test_cluster_signals_without_llm(mock_signals):
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    clusters = generator._cluster_signals(mock_signals, use_llm=False)

    assert len(clusters) == 1
    assert clusters[0]["ticker"] == "2330.TW"
    assert len(clusters[0]["signals"]) == 2
```

**報告契約**：
實作完成後，請在報告中提供以下資訊：
1. 完成的 commit hash（多個 commit 請提供範圍）
2. 測試結果摘要（通過/失敗數量）
3. 任何疑慮或問題（特別是 LLM 驅動邏輯的實作細節）
4. 是否需要額外上下文