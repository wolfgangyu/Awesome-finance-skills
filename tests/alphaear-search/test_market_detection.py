# tests/alphaear-search/test_market_detection.py
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'alphaear-search')))

from scripts.search_tools import SearchTools
from scripts.database_manager import DatabaseManager


class TestMarketDetection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager(":memory:")
        cls.tools = SearchTools(cls.db)

    def test_tw_ticker(self):
        self.assertEqual(self.tools._detect_market("2330"), "tw")
        self.assertEqual(self.tools._detect_market("2454 股價"), "tw")

    def test_us_ticker(self):
        self.assertEqual(self.tools._detect_market("AAPL"), "us")
        self.assertEqual(self.tools._detect_market("NVDA 財報"), "us")

    def test_tw_company_name(self):
        self.assertEqual(self.tools._detect_market("台積電"), "tw")
        self.assertEqual(self.tools._detect_market("聯發科 營收"), "tw")
        self.assertEqual(self.tools._detect_market("鴻海"), "tw")

    def test_us_company_name(self):
        self.assertEqual(self.tools._detect_market("英偉達"), "us")
        self.assertEqual(self.tools._detect_market("蘋果 新產品"), "us")
        self.assertEqual(self.tools._detect_market("Meta"), "us")

    def test_mixed_query(self):
        self.assertEqual(self.tools._detect_market("NVDA 財報"), "us")

    def test_unknown_query(self):
        self.assertIsNone(self.tools._detect_market("最新新聞"))
        self.assertIsNone(self.tools._detect_market("台灣美食"))

    def test_empty(self):
        self.assertIsNone(self.tools._detect_market(""))


class TestEngineSelection(unittest.TestCase):

    def test_engine_selection_returns_valid_engine(self):
        db = DatabaseManager(":memory:")
        tools = SearchTools(db)
        engine = tools._select_engine(None)
        self.assertIsInstance(engine, str)
        self.assertIn(engine, tools._engines)

    def test_engine_selection_us(self):
        db = DatabaseManager(":memory:")
        tools = SearchTools(db)
        engine = tools._select_engine("us")
        self.assertIn(engine, ["jina", "ddg"])

    def test_engine_selection_tw(self):
        db = DatabaseManager(":memory:")
        tools = SearchTools(db)
        engine = tools._select_engine("tw")
        self.assertIn(engine, ["google", "ddg"])


if __name__ == '__main__':
    unittest.main()
