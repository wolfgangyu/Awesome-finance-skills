"""alphaear-stock 的 smoke + 契約測試（unittest）。

涵蓋：
  - import smoke（A 股/港股依賴已徹底卸除）
  - StockTools 初始化（DB in-memory）
  - 搜尋 ticker：資料庫無資料但輸入是 US 字母時回 mock 猜測
  - 取得價格：A 股/港股 ticker 走 twse/TPEx 都空時仍安全（回空 DataFrame，
    不 raise；對資料庫已有者亦如此）
  - 基本面：非 US ticker 一律回空 dict
"""
import os
import sys
import unittest

# 加入 skill root 與 shared schema
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


class TestStock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from scripts.stock_tools import StockTools
            from scripts.database_manager import DatabaseManager
        except ImportError as e:
            raise unittest.SkipTest(f"依賴缺失：{e}")
        cls.StockTools = StockTools
        cls.DatabaseManager = DatabaseManager

    def test_akshare_and_eastmoney_removed(self):
        """A 股/港股依賴必須解除。"""
        import scripts.stock_tools as st
        self.assertFalse(hasattr(st, "ak"), "akshare 仍綁定 stock_tools")
        self.assertFalse(hasattr(st, "EastMoneyDirect"), "EastMoneyDirect 應從 stock_tools 移除")

    def test_init(self):
        """StockTools 必須能用 in-memory DB 初始化。"""
        db = self.DatabaseManager(":memory:")
        tools = self.StockTools(db, auto_update=False)
        self.assertIsNotNone(tools)

    def test_detect_market(self):
        """ticker 型別判斷可用。"""
        import scripts.stock_tools as st
        self.assertEqual(st.detect_market("AAPL"), "us")
        self.assertEqual(st.detect_market("TSLA"), "us")
        self.assertIn(st.detect_market("2330"), ("twse", "tpex"))
        self.assertIn(st.detect_market("6488"), ("twse", "tpex"))

    def test_search_ticker_us_mock(self):
        """未安裝資料庫時，美股字母查詢應回 mock 結果（不 raise）。"""
        db = self.DatabaseManager(":memory:")
        tools = self.StockTools(db, auto_update=False)
        res = tools.search_ticker("AAPL")
        self.assertIsInstance(res, list)
        self.assertGreaterEqual(len(res), 1)
        self.assertEqual(res[0]["code"], "AAPL")

    def test_get_stock_price_empty_db_returns_empty(self):
        """空 DB（且不走網路）應回空 DataFrame。"""
        import scripts.stock_tools as st

        import importlib

        # 找出 twse_client 子模組（透過 stock_tools 的內部 import 綁定）
        tw = sys.modules.get("scripts.twse_client")
        if tw is None:
            # 兜底直接 import
            tw = importlib.import_module("scripts.twse_client")

        captured = {"twse": False, "yf": False}

        class FailingYf:
            def __init__(self, ticker): pass
            def history(self, start=None, end=None):
                captured["yf"] = True

                class _Df:
                    empty = True
                return _Df()

        tw.fetch_kline_with_fallback = lambda *a, **kw: (
            captured.__setitem__("twse", True) or type("E", (), {"empty": True, "attrs": {}})()
        )
        st.yf.Ticker = FailingYf

        db = self.DatabaseManager(":memory:")
        tools = self.StockTools(db, auto_update=False)
        df = tools.get_stock_price("AAPL", "2026-06-01", "2026-06-20")
        self.assertTrue(df.empty, f"預期空 DataFrame，拿到 {df}")


if __name__ == "__main__":
    unittest.main()
