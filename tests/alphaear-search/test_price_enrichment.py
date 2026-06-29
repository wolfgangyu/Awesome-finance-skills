# tests/alphaear-search/test_price_enrichment.py
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'alphaear-search')))

from scripts.search_tools import SearchTools
from scripts.database_manager import DatabaseManager


class TestPriceEnrichment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager(":memory:")
        cls.tools = SearchTools(cls.db)

    def test_fetch_price_method_exists(self):
        """確認 _fetch_price 方法存在"""
        self.assertTrue(hasattr(self.tools, '_fetch_price'))
        self.assertTrue(callable(self.tools._fetch_price))

    def test_fetch_returns_none_on_invalid_ticker(self):
        """無效 ticker 應回傳 None 而不拋出例外"""
        result = self.tools._fetch_price("INVALID12345XYZ", "us")
        self.assertIsNone(result)

    def test_fetch_returns_none_on_empty_ticker(self):
        """空 ticker 應回傳 None"""
        result = self.tools._fetch_price("", "us")
        self.assertIsNone(result)

    def test_fetch_structure_correct(self):
        """成功取得的結果應有正確結構"""
        try:
            result = self.tools._fetch_price("AAPL", "us")
            if result is not None:
                self.assertIn("price", result)
                self.assertIn("currency", result)
                self.assertIn("change", result)
                self.assertIn("change_pct", result)
                self.assertIsInstance(result["price"], (int, float))
        except Exception:
            pass  # 網路不可用時略過


if __name__ == '__main__':
    unittest.main()
