"""
AlphaEar Reporter Python API

供 Polaris 後端 import 使用的 Python API，基於 ReportGenerator 實作。
"""

from typing import List, Dict, Any, Optional
import asyncio
from loguru import logger

from skills.alphaear-reporter.scripts.report_generator import ReportGenerator
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager


class ReportAPI:
    """
    AlphaEar Reporter Python API

    提供簡潔的靜態方法供 Polaris 後端直接呼叫，支援兩種輸出格式：
    - LINE 官方帳號（純文字）
    - LIFF 網頁（HTML）
    """

    @staticmethod
    async def generate_report_for_line(
        signals: List[Dict[str, Any]],
        market: str = "tw",
        user_query: Optional[str] = None,
    ) -> str:
        """
        生成 LINE 官方帳號友好的報告

        Args:
            signals: 投資訊號列表
            market: 市場類型 (預設: "tw")
            user_query: 使用者查詢（可選，用於指導報告方向）

        Returns:
            LINE 官方帳號友好的純文字報告
        """
        logger.info(f"📱 生成 LINE 報告 - 訊號數量: {len(signals)}, 市場: {market}")

        db = DatabaseManager()
        generator = ReportGenerator(db, market=market)

        report = await generator.generate_report(
            signals=signals,
            use_llm=True,  # 預設使用 LLM 驅動邏輯
            user_query=user_query,
        )

        return report["line_friendly"]

    @staticmethod
    async def generate_report_for_liff(
        signals: List[Dict[str, Any]],
        market: str = "tw",
        user_query: Optional[str] = None,
    ) -> str:
        """
        生成 LIFF 網頁用的 HTML 報告

        Args:
            signals: 投資訊號列表
            market: 市場類型 (預設: "tw")
            user_query: 使用者查詢（可選，用於指導報告方向）

        Returns:
            完整的 HTML 報告，包含樣式和結構
        """
        logger.info(f"🌐 生成 LIFF 報告 - 訊號數量: {len(signals)}, 市場: {market}")

        db = DatabaseManager()
        generator = ReportGenerator(db, market=market)

        report = await generator.generate_report(
            signals=signals,
            use_llm=True,  # 預設使用 LLM 驅動邏輯
            user_query=user_query,
        )

        # 生成完整 HTML
        html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlphaEar 報告 - {market.upper()} 市場</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2980b9;
            margin-top: 2em;
        }}
        h3 {{
            color: #3498db;
        }}
        .source {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-top: 1em;
        }}
        .disclaimer {{
            font-size: 0.8em;
            color: #95a5a6;
            border-top: 1px solid #ecf0f1;
            padding-top: 1em;
            margin-top: 2em;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    {report['markdown'].replace('\n', '<br>')}
</body>
</html>
"""

        return html_template

    @staticmethod
    async def generate_report_for_hermes(
        signals: List[Dict[str, Any]],
        market: str = "tw",
        no_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        生成 Hermes Agent 相容的報告格式

        Args:
            signals: 投資訊號列表
            market: 市場類型 (預設: "tw")
            no_llm: 是否禁用 LLM 驅動邏輯（預設: False）

        Returns:
            包含所有格式的報告字典
        """
        logger.info(f"🤖 生成 Hermes 報告 - 訊號數量: {len(signals)}, 市場: {market}, LLM: {not no_llm}")

        db = DatabaseManager()
        generator = ReportGenerator(db, market=market)

        return await generator.generate_report(
            signals=signals,
            use_llm=not no_llm,
        )