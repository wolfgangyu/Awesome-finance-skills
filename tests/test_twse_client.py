"""TWSEClient 與 TPExClient 的契約測試（mock HTTP）。"""
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "alphaear-stock" / "scripts"))

import pandas as pd

import twse_client  # noqa: E402


def _twse_payload(rows):
    """模擬 TWSE 回傳的 JSON 結構。"""
    return {
        "stat": "OK",
        "date": "20260620",
        "data": rows,
        "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    }


def _tpex_payload(rows):
    """模擬 TPEx 回傳的 JSON 結構。"""
    return {
        "stat": "OK",
        "data": rows,
        "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    }


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_twse_returns_schema_columns(monkeypatch):
    """TWSE 回傳的 DataFrame 必須有 date, open, high, low, close, volume 欄位。"""
    rows = [
        ["114/06/20", "1,234,567", "987,654,321", "100.00", "105.50", "99.00", "104.00", "+1.50", "1,234"],
        ["114/06/19", "2,345,678", "888,111,222", "101.00", "106.00", "100.00", "102.50", "+0.50", "2,345"],
    ]
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(_twse_payload(rows))

    monkeypatch.setattr(twse_client.requests, "get", fake_get)

    df = twse_client.fetch_kline_twse("2330", "2026-06-01", "2026-06-20")

    assert "date" in df.columns and "open" in df.columns
    assert "high" in df.columns and "low" in df.columns
    assert "close" in df.columns and "volume" in df.columns
    assert len(df) == 2
    assert df.iloc[0]["close"] == 104.00
    assert captured["params"]["stockNo"] == "2330"
    assert captured["url"].startswith("https://www.twse.com.tw")


def test_tpex_returns_schema_columns(monkeypatch):
    """TPEx 回傳同樣契約。"""
    rows = [
        ["114/06/20", "1,000,000", "100,000,000", "50.00", "52.00", "49.00", "51.00", "+1.00", "500"],
    ]

    def fake_get(url, params=None, timeout=None):
        return FakeResponse(_tpex_payload(rows))

    monkeypatch.setattr(twse_client.requests, "get", fake_get)

    df = twse_client.fetch_kline_tpex("6488", "2026-06-01", "2026-06-20")

    assert len(df) == 1
    assert df.iloc[0]["close"] == 51.00


def test_twse_returns_empty_when_api_blank(monkeypatch):
    """TWSE 沒資料時要回空 DataFrame，不要 raise。"""
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"stat": "OK", "data": [], "fields": []})

    monkeypatch.setattr(twse_client.requests, "get", fake_get)
    df = twse_client.fetch_kline_twse("9999", "2026-06-01", "2026-06-20")
    assert df.empty


def test_twse_raises_on_http_error(monkeypatch):
    """HTTP 4xx/5xx 必須 raise，不能吞掉。"""
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({}, status_code=500)

    monkeypatch.setattr(twse_client.requests, "get", fake_get)
    try:
        twse_client.fetch_kline_twse("2330", "2026-06-01", "2026-06-20")
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError on HTTP 500")


def test_routes_correct_market():
    """detect_market() 區分 TWSE 上市/上櫃/美股。"""
    # TWSE 上市：4 位數字（不含 6 開頭但實際上 4 位都是 TWSE, 5 位有 6 開頭可能是 ETF）
    assert twse_client.detect_market("2330") == "twse"
    assert twse_client.detect_market("0050") == "twse"
    # TPEx 上櫃：4 位數字開頭 8、9 不可靠，CSV 規則：ticker 用 4-6 位英數字
    assert twse_client.detect_market("6488") == "tpex"
    # 美股: 純字母
    assert twse_client.detect_market("AAPL") == "us"
    assert twse_client.detect_market("TSLA") == "us"
