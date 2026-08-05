# Task 5: Agentic Workflow 相容性修改

**專案脈絡**：
本任務修改現有的 `report_agent.py`，使其使用 Task 2 實作的 `ReportGenerator`，保持與現有 Agentic Workflow 的相容性。

**檔案**：
- Modify: `skills/alphaear-reporter/scripts/report_agent.py:1-50`
- Test: `tests/test_reporter.py`（現有測試）

**修改內容**：
```python
from .report_generator import ReportGenerator  # Task 2 實作
from .utils.database_manager import DatabaseManager

class ReportAgent:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.generator = ReportGenerator(db)

    async def generate_report(self, signals):
        """相容現有 Agentic Workflow"""
        return await self.generator.generate_report(signals, use_llm=True)
```

**測試**：
```python
import pytest
from skills.alphaear-reporter.scripts.report_agent import ReportAgent
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager

@pytest.mark.asyncio
async def test_report_agent_compatibility():
    db = DatabaseManager(":memory:")
    agent = ReportAgent(db)

    signals = [{"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}]
    report = await agent.generate_report(signals)

    assert "研報" in report["markdown"]
```

**報告契約**：
實作完成後，請在報告中提供以下資訊：
1. 完成的 commit hash
2. 測試結果摘要
3. 任何相容性問題（特別是現有 prompt 的相容性）
4. 是否需要額外上下文