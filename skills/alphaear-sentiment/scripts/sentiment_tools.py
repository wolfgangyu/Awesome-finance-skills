"""SentimentTools with automated keyword scoring.

Now supports:
- Manual scoring (Agent-driven)
- Automated keyword scoring (for zh-TW, ja, en)
- Batch processing with language detection
- Matched keywords saved to meta_data
"""

import os
from typing import Dict, List, Union, Optional
import json
from loguru import logger
from .database_manager import DatabaseManager
from .keyword_scorer import KeywordScorer


class SentimentTools:
    """
    情緒分析工具 — 支援 Agent 手動分析與自動關鍵字評分。

    自動評分支援語言：繁體中文 (zh-TW)、日文 (ja)、英文 (en)。
    """

    def __init__(self, db: DatabaseManager):
        """
        初始化情緒分析工具。

        Args:
            db: 資料庫管理器實例
        """
        self.db = db
        self.keyword_scorer = KeywordScorer()

    def update_single_news_sentiment(self, news_id: Union[str, int], score: float, reason: str = "") -> bool:
        """
        將 Agent 分析的情緒結果保存到資料庫。

        Args:
            news_id: 新聞 ID
            score: -1.0 到 1.0
            reason: 分析理由

        Returns:
            Success bool
        """
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

    def auto_score_news(self, news_item: Dict) -> bool:
        """
        自動對單篇新聞進行關鍵字評分並保存結果（含 matched_keywords）。

        Args:
            news_item: 新聞 dict（需套件含 id, title, content, meta_data 欄位）

        Returns:
            Success bool
        """
        try:
            news_id = news_item.get('id')
            title = news_item.get('title', '')
            content = news_item.get('content', '')
            meta_data = news_item.get('meta_data', {})

            # 確保 meta_data 是 dict
            if isinstance(meta_data, str):
                try:
                    meta_data = json.loads(meta_data)
                except:
                    meta_data = {}

            # 從 meta_data 取得語言（如果有）
            language = meta_data.get('language')

            # 執行關鍵字評分
            result = self.keyword_scorer.score_news(title, content, language)

            # 保存 matched_keywords 到 meta_data
            meta_data["sentiment_keywords"] = result["matched_keywords"]

            # 更新資料庫
            cursor = self.db.conn.cursor()
            cursor.execute("""
                UPDATE daily_news
                SET sentiment_score = ?,
                    meta_data = ?
                WHERE id = ?
            """, (result["score"], json.dumps(meta_data), news_id))
            self.db.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to auto-score news {news_item.get('id')}: {e}")
            return False

    def batch_update_news_sentiment(self, source: Optional[str] = None, limit: int = 50) -> int:
        """
        批量更新資料庫中新聞的情緒分數。

        自動偵測新聞語言並使用關鍵字評分，同時保存匹配的關鍵字到 meta_data。

        Args:
            source: 篩選特定新聞源，如 "cna_finance"。None 則處理所有來源。
            limit: 最多處理的新聞數量。

        Returns:
            成功更新的新聞數量。
        """
        news_items = self.db.get_daily_news(source=source, limit=limit)
        to_analyze = [item for item in news_items if not item.get('sentiment_score')]

        if not to_analyze:
            logger.info("No unanalyzed news items found.")
            return 0

        success_count = 0
        for item in to_analyze:
            try:
                if self.auto_score_news(item):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error processing news {item.get('id')}: {e}")

        logger.info(f"✅ Auto-scored {success_count}/{len(to_analyze)} news items using keyword matching.")
        return success_count