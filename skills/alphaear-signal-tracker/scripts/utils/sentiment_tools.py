import os
from typing import Dict, Optional, Union
import json
from loguru import logger
from agno.agent import Agent
from .llm.factory import get_model
from .database_manager import DatabaseManager

# 讀取預設情緒分析模式
DEFAULT_SENTIMENT_MODE = os.getenv("SENTIMENT_MODE", "llm")  # llm

class SentimentTools:
    """
    情緒分析工具 - 僅使用 LLM 進行深度情緒分析

    模式說明:
    - "llm": 使用 LLM 分析（準確但較慢）

    可透過環境變數 SENTIMENT_MODE 設定預設模式。
    """

    def __init__(self, db: DatabaseManager, mode: Optional[str] = None,
                 model_provider: str = "openai", model_id: str = "gpt-4o"):
        """
        初始化情緒分析工具。

        Args:
            db: 資料庫管理器實例
            mode: 分析模式，可選 "llm"。None 則使用環境變數預設值。
            model_provider: LLM 提供商，如 "openai", "ust", "deepseek"
            model_id: 模型識別符
        """
        self.db = db
        self.mode = mode or DEFAULT_SENTIMENT_MODE
        self.llm_model = None

        # Initialize LLM
        try:
            provider = "ust" if os.getenv("UST_KEY_API") else model_provider
            m_id = "Qwen" if provider == "ust" else model_id
            self.llm_model = get_model(provider, m_id)
        except Exception as e:
            logger.warning(f"LLM initialization skipped: {e}")

    def analyze_sentiment(self, text: str) -> Dict[str, Union[float, str]]:
        """
        分析文本的情緒極性。使用 LLM 進行分析。

        Args:
            text: 需要分析的文本內容，如新聞標題或摘要。

        Returns:
            包含以下字段的字典:
            - score: 情緒分值，範圍 -1.0（極度負面）到 1.0（極度正面），0.0 為中性
            - label: 情緒標籤，"positive"/"negative"/"neutral"
            - reason: 分析理由
        """
        return self.analyze_sentiment_llm(text)

    def analyze_sentiment_llm(self, text: str) -> Dict[str, Union[float, str]]:
        """
        使用 LLM 進行深度情緒分析，可獲得詳細的分析理由。

        Args:
            text: 需要分析的文本，最多處理前 1000 字元。

        Returns:
            包含 score, label, reason 的字典。
        """
        if not self.llm_model:
            return {"score": 0.0, "label": "neutral", "error": "LLM not initialized"}

        analyzer = Agent(model=self.llm_model, markdown=True)
        prompt = f"""請分析以下金融/新聞文本的情緒極性。
        回傳嚴格的 JSON 格式:
        {{"score": <float: -1.0到1.0>, "label": "<positive/negative/neutral>", "reason": "<簡短理由>"}}

        文本: {text[:1000]}"""

        try:
            response = analyzer.run(prompt)
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM sentiment failed: {e}")
            return {"score": 0.0, "label": "error", "reason": str(e)}

    def batch_update_news_sentiment(self, source: Optional[str] = None, limit: int = 50):
        """
        批量更新資料庫中新聞的情緒分數。

        Args:
            source: 篩選特定新聞源，如 "wallstreetcn"。None 則處理所有來源。
            limit: 最多處理的新聞數量。

        Returns:
            成功更新的新聞數量。
        """
        news_items = self.db.get_daily_news(source=source, limit=limit)
        to_analyze = [item for item in news_items if not item.get('sentiment_score')]

        if not to_analyze:
            return 0

        logger.info(f"Analyzing {len(to_analyze)} items with LLM...")

        updated_count = 0
        cursor = self.db.conn.cursor()

        for item in to_analyze:
            analysis = self.analyze_sentiment_llm(item['title'])
            cursor.execute("""
                UPDATE daily_news
                SET sentiment_score = ?, meta_data = json_set(COALESCE(meta_data, '{}'), '$.sentiment_reason', ?)
                WHERE id = ?
            """, (analysis.get('score', 0.0), analysis.get('reason', ''), item['id']))
            updated_count += 1

        self.db.conn.commit()
        return updated_count
