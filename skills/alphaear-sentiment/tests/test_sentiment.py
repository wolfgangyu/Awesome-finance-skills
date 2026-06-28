"""alphaear-sentiment 的 smoke 測試（unittest）。

涵蓋：
  - import smoke
  - SentimentTools 初始化（無需額外相依）
  - update_single_news_sentiment 方法存在
"""
import os
import sys
import unittest

# 加入 skill root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSentiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from scripts.sentiment_tools import SentimentTools
            from scripts.database_manager import DatabaseManager
        except ImportError as e:
            raise unittest.SkipTest(f"依賴缺失：{e}")
        cls.SentimentTools = SentimentTools
        cls.DatabaseManager = DatabaseManager

    def test_init(self):
        """SentimentTools 必須能用 in-memory DB 初始化，且不需要 transformers。"""
        db = self.DatabaseManager(":memory:")
        tools = self.SentimentTools(db)
        self.assertIsNotNone(tools)

    def test_update_sentiment(self):
        """update_single_news_sentiment 方法必須存在且可呼叫。"""
        db = self.DatabaseManager(":memory:")
        tools = self.SentimentTools(db)
        # 測試方法存在（不一定要寫入成功，因為 daily_news 可能無對應資料）
        self.assertTrue(hasattr(tools, 'update_single_news_sentiment'))
        self.assertTrue(hasattr(tools, 'batch_update_news_sentiment'))


if __name__ == "__main__":
    unittest.main()
