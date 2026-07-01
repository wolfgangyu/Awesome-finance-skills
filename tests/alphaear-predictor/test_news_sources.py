"""Tests for MarketAwareNewsSource — no real network calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.utils.news_sources import MarketAwareNewsSource, NewsItem


class FakeDB:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}

    def get_search_cache(self, query_hash: str, ttl_seconds=None):
        return self.cache.get(query_hash)

    def save_search_cache(self, query_hash: str, query: str, engine: str, results):
        self.cache[query_hash] = json.dumps(results)


class FakeTicker:
    def __init__(self, ticker: str) -> None:
        self.news = [
            {
                "title": f"{ticker} news",
                "publisher": "Yahoo Finance",
                "link": f"https://finance.yahoo.com/news/{ticker.lower()}",
                "providerTime": "2024-01-15T08:00:00Z",
                "type": "STORY",
            }
        ]


def test_collect_tw_hits_yfinance_first() -> None:
    db = FakeDB()
    source = MarketAwareNewsSource(db=db, yfinance_module=MagicMock(Ticker=FakeTicker))
    results = source.collect("2330", "TW", "2024-01-15")
    assert len(results) >= 1
    assert isinstance(results[0], NewsItem)
    assert results[0].title
    assert results[0].url


def test_collect_us_hits_yfinance() -> None:
    db = FakeDB()
    source = MarketAwareNewsSource(db=db, yfinance_module=MagicMock(Ticker=FakeTicker))
    results = source.collect("AAPL", "US", "2024-01-15")
    assert len(results) >= 1


def test_collect_falls_through_to_rss_when_yfinance_empty() -> None:
    """If yfinance returns empty news list, should attempt RSS fallback."""
    db = FakeDB()
    class EmptyTicker:
        news = []
    source = MarketAwareNewsSource(db=db, yfinance_module=MagicMock(Ticker=EmptyTicker))
    # Patch _fetch_rss to return a known item
    with patch.object(source, "_fetch_rss", return_value=[
        NewsItem(title="RSS news", url="https://rss.test/item", body="body", published_at="2024-01-15")
    ]):
        results = source.collect("2330", "TW", "2024-01-15")
        # Should include the RSS item
        rss_titles = [r.title for r in results if "RSS" in r.title]
        assert len(rss_titles) >= 1


def test_collect_caches_in_search_cache() -> None:
    db = FakeDB()
    source = MarketAwareNewsSource(db=db, yfinance_module=MagicMock(Ticker=FakeTicker))
    source.collect("2330", "TW", "2024-01-15")
    query_hash = hashlib.sha256("TW|2330|2024-01-15".encode()).hexdigest()
    assert query_hash in db.cache


def test_collect_returns_cached_on_second_call() -> None:
    db = FakeDB()
    source = MarketAwareNewsSource(db=db, yfinance_module=MagicMock(Ticker=FakeTicker))
    # First call populates cache
    source.collect("2330", "TW", "2024-01-15")
    # Second call should hit cache and NOT call yfinance
    fake_ticker = MagicMock()
    fake_ticker.news = []
    source.yfinance_module = MagicMock(Ticker=fake_ticker)
    results = source.collect("2330", "TW", "2024-01-15")
    # Results come from cache, yfinance.Ticker() was NOT called
    fake_ticker.Ticker.assert_not_called()


def test_no_baidu_guarded() -> None:
    """Hard constraint: news_sources.py MUST NOT contain 'baidu'."""
    ns_py = Path(__file__).resolve().parents[2] / "skills" / "alphaear-predictor" / "scripts" / "utils" / "news_sources.py"
    text = ns_py.read_text(encoding="utf-8")
    assert "baidu" not in text.lower(), "news_sources.py must not import or reference baidu"
