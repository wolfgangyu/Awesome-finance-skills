"""StockTools 重構後的契約測試（mock 網路層）。

這個檔案**故意不依賴 pytest**。每個 test_* 函式會使用極簡 `_Patch` 工具，
可在沒有 pytest 的環境下跑（`python tests/test_stock_tools_refactored.py`）。
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "alphaear-stock" / "scripts"


def _reload_top_level():
    """重載並回傳四個 module 的 tuple：(stock_tools, twse_client, db manager, yfinance 套件)。

    把 taiwan 測試需要的子模組一次拿齊。
    """
    if str(SCRIPTS.parent) not in sys.path:
        sys.path.insert(0, str(SCRIPTS.parent))
    for mod in list(sys.modules):
        if mod.startswith("stock_tools") or mod.startswith("twse_client") or mod.startswith("scripts") or mod.startswith("scripts."):
            del sys.modules[mod]
    import scripts  # noqa: F401
    from scripts import stock_tools as st
    from scripts import twse_client as tc
    from scripts import database_manager as dm
    import yfinance as yf

    importlib.reload(tc)
    importlib.reload(dm)
    importlib.reload(st)
    return st, tc, dm.DatabaseManager, yf


_MISSING = object()


class _Patch:
    """極簡 monkeypatch：紀錄原值，restore 時還原。"""

    def __init__(self):
        self.patches = []

    def setattr(self, obj, attr, value):
        original = getattr(obj, attr, _MISSING)
        self.patches.append((obj, attr, original))
        setattr(obj, attr, value)

    def restore(self):
        for obj, attr, original in self.patches:
            if original is _MISSING:
                try:
                    delattr(obj, attr)
                except AttributeError:
                    pass
            else:
                setattr(obj, attr, original)


import pandas as pd   # noqa: E402
import requests   # noqa: E402


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_detect_market_exposed():
    st, _, _, _ = _reload_top_level()
    assert hasattr(st, "detect_market")
    assert st.detect_market("2330") in ("twse", "tpex")
    assert st.detect_market("AAPL") == "us"


def test_get_stock_price_us_uses_yfinance():
    st, tw, DatabaseManager, yf = _reload_top_level()
    p = _Patch()
    twse_called = {"value": False}

    def fail_get(*args, **kwargs):
        twse_called["value"] = True
        raise AssertionError("TWSE 不該被美股路徑呼叫")

    p.setattr(requests, "get", fail_get)

    history = pd.DataFrame({
        "Date": pd.to_datetime(["2026-06-19", "2026-06-20"]),
        "Open": [100.0, 102.0],
        "Close": [101.0, 103.0],
        "High": [102.0, 104.0],
        "Low": [99.0, 101.0],
        "Volume": [1000, 2000],
    })

    class FakeTicker:
        def __init__(self, ticker): pass

        def history(self, start=None, end=None):
            return history

    p.setattr(yf, "Ticker", FakeTicker)

    try:
        db = DatabaseManager(":memory:")
        tools = st.StockTools(db, auto_update=False)
        df = tools.get_stock_price("AAPL", "2026-06-01", "2026-06-20")
        assert not twse_called["value"], "TWSE 不該被呼叫"
        assert not df.empty
        assert df["close"].iloc[-1] == 103.0
    finally:
        p.restore()


def test_get_stock_price_tw_uses_twse():
    st, tw, DatabaseManager, yf = _reload_top_level()
    p = _Patch()
    yf_called = {"value": False}

    class FailingTicker:
        def __init__(self, ticker): pass

        def history(self, start=None, end=None):
            yf_called["value"] = True
            raise AssertionError("yfinance 不該被台股路徑呼叫")

    p.setattr(yf, "Ticker", FailingTicker)

    twse_payload = {
        "stat": "OK",
        "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
        "data": [
            ["115/06/20", "1,000,000", "123,456,789", "100.00", "105.00", "99.00", "104.00", "+1.50", "123"],
        ],
    }

    def fake_get(url, params=None, timeout=None):
        return FakeResponse(twse_payload)

    p.setattr(requests, "get", fake_get)

    try:
        db = DatabaseManager(":memory:")
        tools = st.StockTools(db, auto_update=False)
        df = tools.get_stock_price("2330", "2026-06-01", "2026-06-20")
        assert not yf_called["value"]
        assert not df.empty
        assert df["close"].iloc[0] == 104.00
    finally:
        p.restore()


def test_get_stock_price_unknown_ticker_returns_empty():
    st, tw, DatabaseManager, yf = _reload_top_level()
    p = _Patch()

    def empty_get(url, params=None, timeout=None):
        return FakeResponse({"stat": "OK", "fields": [], "data": []})

    p.setattr(requests, "get", empty_get)

    class FailingTicker:
        def __init__(self, ticker): pass
        def history(self, start=None, end=None):
            return pd.DataFrame()

    p.setattr(yf, "Ticker", FailingTicker)

    try:
        db = DatabaseManager(":memory:")
        tools = st.StockTools(db, auto_update=False)
        df = tools.get_stock_price("ZZ9999", "2026-06-01", "2026-06-20")
        assert df.empty
    finally:
        p.restore()


def test_akshare_and_eastmoney_removed():
    st, _, _, _ = _reload_top_level()
    assert not hasattr(st, "ak"), "akshare 仍是 stock_tools 的依賴"
    assert not hasattr(st, "EastMoneyDirect"), "EastMoneyDirect 應從 stock_tools 移除"


def test_get_stock_fundamentals_us_works():
    st, _, DatabaseManager, yf = _reload_top_level()
    p = _Patch()

    info = {
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "marketCap": 3_000_000_000_000,
        "trailingPE": 30.5,
        "longBusinessSummary": "Apple designs and sells consumer electronics.",
        "currency": "USD",
    }

    class FakeTicker:
        def __init__(self, ticker): pass

        @property
        def info(self_inner):
            return info

    p.setattr(yf, "Ticker", FakeTicker)
    try:
        db = DatabaseManager(":memory:")
        tools = st.StockTools(db, auto_update=False)
        result = tools.get_stock_fundamentals("AAPL")
        assert result["name"] == "Apple Inc."
        assert result["currency"] == "USD"
        assert result["pe_ratio"] == 30.5
    finally:
        p.restore()


def test_get_stock_fundamentals_tw_returns_empty():
    st, _, DatabaseManager, _ = _reload_top_level()
    db = DatabaseManager(":memory:")
    tools = st.StockTools(db, auto_update=False)
    info = tools.get_stock_fundamentals("2330")
    assert info in (None, {}), f"台股基本面應回空，但拿到 {info!r}"


if __name__ == "__main__":
    import traceback

    tests = sorted(name for name, obj in globals().items()
                   if name.startswith("test_") and callable(obj))
    failures = []
    for t in tests:
        try:
            globals()[t]()
            print(f"PASS  {t}")
        except Exception:
            print(f"FAIL  {t}")
            traceback.print_exc()
            failures.append(t)
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    if failures:
        raise SystemExit(1)
