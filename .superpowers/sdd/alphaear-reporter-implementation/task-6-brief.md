# Task 6: 整合測試與文件更新

**專案脈絡**：
本任務完成 alphaear-reporter 統一設計的最後階段，包括整合測試和文件更新。

**檔案**：
- Create: `tests/test_integration.py`
- Modify: `skills/alphaear-reporter/SKILL.md`

**整合測試**：
```python
import pytest
from skills.alphaear-reporter.scripts.report_generator import ReportGenerator
from skills.alphaear-reporter.scripts.report_cli import generate_report_cli
from skills.alphaear-reporter.scripts.report_api import ReportAPI
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager

@pytest.mark.asyncio
async def test_integration():
    """整合測試：三種場景使用相同核心邏輯"""
    signals = [{"title": "整合測試", "content": "測試內容", "ticker": "2330.TW"}]
    db = DatabaseManager(":memory:")

    # 1. ReportGenerator
    generator = ReportGenerator(db)
    report = await generator.generate_report(signals, use_llm=False)
    assert "整合測試" in report["markdown"]

    # 2. CLI（模擬）
    class Args:
        signals = '[{"title": "CLI 測試", "content": "測試", "ticker": "2330.TW"}]'
        market = "tw"
        output = "line"
        no_llm = True
    await generate_report_cli(Args())
    # 輸出驗證透過 capsys

    # 3. Python API
    line_report = await ReportAPI.generate_report_for_line(signals)
    assert "【研報】" in line_report
```

**文件更新**：
更新 `SKILL.md` 新增以下內容：

```markdown
## 新增功能：統一設計

本次更新新增三種使用方式：

1. **CLI 介面**（供 Hermes Agent 呼叫）
   ```bash
   python -m skills.alphaear-reporter.scripts.report_cli \
     --signals '[{"title": "台積電營收", "content": "...", "ticker": "2330.TW"}]' \
     --output line
   ```

2. **Python API**（供 Polaris 後端 import）
   ```python
   from skills.alphaear-reporter.scripts.report_api import ReportAPI

   report = await ReportAPI.generate_report_for_line(signals)
   ```

3. **相容現有 Agentic Workflow**（供 Claude Code 使用）
   ```python
   from skills.alphaear-reporter.scripts.report_agent import ReportAgent

   agent = ReportAgent(db)
   report = await agent.generate_report(signals)
   ```
```

**報告契約**：
實作完成後，請在報告中提供以下資訊：
1. 完成的 commit hash
2. 測試結果摘要
3. 任何整合問題
4. 是否需要額外上下文