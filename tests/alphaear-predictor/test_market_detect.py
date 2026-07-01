"""Pure-function tests for market_detect module."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

# Ensure predictor skill dir is on sys.path so scripts.* imports work.
_PREDICTOR_SKILL = Path(__file__).resolve().parents[2] / "skills" / "alphaear-predictor"
if str(_PREDICTOR_SKILL) not in sys.path:
    sys.path.insert(0, str(_PREDICTOR_SKILL))

from scripts.utils.market_detect import detect_market, legacy_market_code, resolve_name


class FakeDB:
    def __init__(self, mapping: dict[str, dict[str, str]] | None = None) -> None:
        self.mapping = mapping or {}

    def get_stock_by_code(self, code: str):
        return self.mapping.get(code)


def test_detect_tw_four_digit() -> None:
    assert detect_market("2330") == "TW"
    assert detect_market("0113") == "TW"


def test_detect_tw_with_TW_suffix() -> None:
    assert detect_market("2330.TW") == "TW"


def test_detect_tw_four_digit_leading_zero() -> None:
    assert detect_market("0079") == "TW"


def test_detect_us_letters() -> None:
    assert detect_market("AAPL") == "US"
    assert detect_market("NVDA") == "US"


def test_detect_crypto_dash() -> None:
    assert detect_market("BTC-USD") == "CRYPTO"


def test_detect_crypto_slash() -> None:
    assert detect_market("BTC/USDT") == "CRYPTO"


def test_detect_other() -> None:
    assert detect_market("XYZ123") == "OTHER"
    assert detect_market("not_a_ticker") == "OTHER"


def test_resolve_name_tw_falls_back_to_db() -> None:
    db = FakeDB({"2330": {"code": "2330", "name": "TSMC"}})
    assert resolve_name("2330", "TW", db=db) == "TSMC"


def test_resolve_name_tw_db_missing_falls_back_to_ticker() -> None:
    db = FakeDB({})
    assert resolve_name("9999", "TW", db=db) == "9999"


def test_resolve_name_us_uses_yfinance_info() -> None:
    class FakeYf:
        class Ticker:
            def __init__(self, _ticker: str) -> None:
                self.info = {"longName": "Apple Inc."}
    assert resolve_name("AAPL", "US", yfinance_module=FakeYf) == "Apple Inc."


def test_resolve_name_us_no_longname_returns_ticker() -> None:
    class FakeYf:
        class Ticker:
            def __init__(self, _ticker: str) -> None:
                self.info = {}
    assert resolve_name("AAPL", "US", yfinance_module=FakeYf) == "AAPL"


def test_resolve_name_crypto() -> None:
    assert resolve_name("BTC-USD", "CRYPTO") == "BTC-USD"


def test_resolve_name_other() -> None:
    assert resolve_name("XYZ123", "OTHER") == "XYZ123"


def test_legacy_market_code_tw() -> None:
    assert legacy_market_code("2330") == "twse"


def test_legacy_market_code_us() -> None:
    assert legacy_market_code("AAPL") == "us"
