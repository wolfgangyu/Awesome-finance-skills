# Task 4: Python API 實作

**專案脈絡**：
本任務實作 alphaear-reporter 的 Python API，供 Polaris 後端 import 使用。這是統一設計的第三個進入點，基於 Task 2 實作的 `ReportGenerator`。

**檔案**：
- Create: `skills/alphaear-reporter/scripts/report_api.py`
- Test: `tests/test_reporter_api.py`

**介面定義**：
```python
from typing import List, Dict, Any
from .report_generator import ReportGenerator  # Task 2 實作
from .utils.database_manager import DatabaseManager

class ReportAPI:
    """供 Polaris 後端 import 使用的 API"""

    @staticmethod
    async def generate_report_for_line(
        signals: List[Dict[str, Any]],
        market: str = "tw",
    ) -> str:
        """生成 LINE 官方帳號友好的報告"""
        db = DatabaseManager()
        generator = ReportGenerator(db, market=market)
        report = await generator.generate_report(signals, use_llm=True)
        return report["line_friendly"]

    @staticmethod
    async def generate_report_for_liff(
        signals: List[Dict[str, Any]],
        market: str = "tw",
    ) -> str:
        """生成 LIFF 網頁用的 HTML 報告"""
        db = DatabaseManager()
        generator = ReportGenerator(db, market=market)
        report = await generator.generate_report(signals, use_llm=True)
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>AlphaEar 報告</title>
        </head>
        <body>
            <div style="white-space: pre-wrap;">{report['markdown']}</div>
        </body>
        </html>
        """
```

**測試**：
```python
import pytest
from skills.alphaear-reporter.scripts.report_api import ReportAPI

@pytest.mark.asyncio
async def test_report_api():
    signals = [{"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}]

    line_report = await ReportAPI.generate_report_for_line(signals)
    assert "【研報】" in line_report

    liff_report = await ReportAPI.generate_report_for_liff(signals)
    assert "<title>AlphaEar 報告</title>" in liff_report
```

**報告契約**：
實作完成後，請在報告中提供以下資訊：
1. 完成的 commit hash
2. 測試結果摘要
3. 任何疑慮或問題（特別是 HTML 輸出格式和安全性）
4. 是否需要額外上下文