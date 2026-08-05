# Task 3: CLI 介面實作

**專案脈絡**：
本任務實作 alphaear-reporter 的 CLI 介面，供 Hermes Agent 呼叫。這是統一設計的第二個進入點，基於 Task 2 實作的 `ReportGenerator`。

**檔案**：
- Create: `skills/alphaear-reporter/scripts/report_cli.py`
- Test: `tests/test_reporter_cli.py`

**介面定義**：
```python
import argparse
import json
import asyncio
from .report_generator import ReportGenerator  # Task 2 實作
from .utils.database_manager import DatabaseManager

async def generate_report_cli(args):
    """CLI 入口邏輯"""
    db = DatabaseManager()
    generator = ReportGenerator(db, market=args.market)

    signals = json.loads(args.signals)

    report = await generator.generate_report(
        signals=signals,
        use_llm=not args.no_llm,
    )

    if args.output == "markdown":
        print(report["markdown"])
    elif args.output == "json":
        print(json.dumps(report["json"], ensure_ascii=False))
    elif args.output == "line":
        print(report["line_friendly"])

def main():
    parser = argparse.ArgumentParser(description="AlphaEar Reporter CLI")
    parser.add_argument("--signals", type=str, required=True, help="JSON string of input signals")
    parser.add_argument("--market", type=str, default="tw", choices=["tw", "us", "both"])
    parser.add_argument("--output", type=str, default="markdown", choices=["markdown", "json", "line"])
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM (simplified logic)")
    args = parser.parse_args()

    asyncio.run(generate_report_cli(args))

if __name__ == "__main__":
    main()
```

**測試**：
```python
import pytest
from skills.alphaear-reporter.scripts.report_cli import generate_report_cli
import asyncio
import io
import sys

@pytest.mark.asyncio
async def test_cli_output(capsys):
    signals = '[{"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}]'
    args = type('Args', (), {
        'signals': signals,
        'market': 'tw',
        'output': 'line',
        'no_llm': True
    })()

    await generate_report_cli(args)

    captured = capsys.readouterr()
    assert "【研報】" in captured.out
```

**報告契約**：
實作完成後，請在報告中提供以下資訊：
1. 完成的 commit hash
2. 測試結果摘要
3. 任何疑慮或問題（特別是 CLI 參數解析和錯誤處理）
4. 是否需要額外上下文