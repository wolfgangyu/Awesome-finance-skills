"""
AlphaEar Reporter Agentic Workflow 相容性修改

將現有的 ReportAgent 修改為使用 ReportGenerator，保持與現有 Agentic Workflow 的相容性。
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from .utils.database_manager import DatabaseManager
from .report_generator import ReportGenerator


class ReportAgent:
    """
    相容現有 Agentic Workflow 的報告生成器

    此類別作為現有 Agentic Workflow 與新 ReportGenerator 之間的橋樑，
    保持相同的介面但使用新的核心邏輯。
    """

    def __init__(self, db: DatabaseManager):
        """
        初始化 ReportAgent

        Args:
            db: DatabaseManager 實例
        """
        self.db = db
        self.generator = ReportGenerator(db)
        logger.info("🤖 ReportAgent 初始化完成 - 使用 ReportGenerator 核心邏輯")

    async def generate_report(
        self,
        signals: List[Dict[str, Any]],
        market: str = "tw",
        user_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成研究報告（相容現有 Agentic Workflow 介面）

        Args:
            signals: 投資訊號列表
            market: 市場類型（預設: "tw"）
            user_query: 使用者查詢（可選，用於指導報告方向）

        Returns:
            報告字典，包含:
            - "markdown": 完整 Markdown 格式報告
            - "json": 結構化 JSON 報告
            - "line_friendly": LINE 官方帳號友好格式
        """
        logger.info(f"📊 ReportAgent 生成報告 - 訊號數量: {len(signals)}, 市場: {market}")

        # 更新 generator 的市場設定
        self.generator.market = market

        # 使用 ReportGenerator 生成報告
        report = await self.generator.generate_report(
            signals=signals,
            use_llm=True,  # 預設使用 LLM 驅動邏輯
            user_query=user_query,
        )

        return report

    @staticmethod
    def build_structured_report(
        report_md: str,
        signals: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        相容現有介面的結構化報告解析

        Args:
            report_md: Markdown 格式報告
            signals: 原始訊號列表
            clusters: 主題簇列表

        Returns:
            結構化 JSON 報告
        """
        # 使用 ReportGenerator 的解析邏輯
        from .report_generator import ReportGenerator
        return ReportGenerator._parse_to_json(ReportGenerator(None), report_md)