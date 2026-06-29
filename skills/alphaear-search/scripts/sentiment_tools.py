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
        """將 Agent 分析的情緒結果儲存到資料庫。"""
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
        """批次更新資料庫中新聞的情緒分數 — 由 Agent 自行執行分析。"""
        news_items = self.db.get_daily_news(source=source, limit=limit)
        to_analyze = [item for item in news_items if not item.get('sentiment_score')]
        if not to_analyze:
            return 0
        logger.info(f"📝 {len(to_analyze)} unanalyzed news items found. Agent should perform sentiment analysis and call update_single_news_sentiment for each.")
        return 0
