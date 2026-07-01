"""Market-aware news collection for TW/US fine-tuning.

Collects news via yfinance.Ticker.news (primary) and RSS feeds (secondary).
Caches results in the existing DatabaseManager.search_cache table.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import List, Optional

import requests
from loguru import logger


class NewsItem:
    """Normalized news item returned by collect()."""

    def __init__(
        self,
        title: str,
        url: str,
        body: str = "",
        published_at: str = "",
    ) -> None:
        self.title = title
        self.url = url
        self.body = body
        self.published_at = published_at

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "body": self.body,
            "published_at": self.published_at,
        }


class MarketAwareNewsSource:
    """Collects news for a (ticker, market, shock_date) triple."""

    # RSS endpoints — configurable for future expansion
    RSS_ENDPOINTS: dict[str, str] = {
        "TW": "https://feeds.feedburner.com/rsscna/finance",
        "US": "https://news.google.com/rss/search?q=",
    }

    def __init__(
        self,
        db=None,
        yfinance_module=None,
    ) -> None:
        self.db = db
        self.yfinance_module = yfinance_module or __import__("yfinance")

    # --- public ---

    def collect(
        self,
        ticker: str,
        market: str,
        shock_date: str,
    ) -> List[NewsItem]:
        """Collect news for ``ticker`` on ``shock_date``, respecting cache."""
        query_hash = hashlib.sha256(
            f"{market}|{ticker}|{shock_date}".encode()
        ).hexdigest()

        # Check search_cache first
        if self.db is not None:
            cached = self.db.get_search_cache(query_hash)
            if cached is not None:
                if isinstance(cached, dict):
                    results = cached.get("results")
                    if isinstance(results, str):
                        results = json.loads(results)
                    if results:
                        logger.debug("Cache hit for {}", query_hash)
                        return [NewsItem(**item) for item in results]
                elif isinstance(cached, str):
                    try:
                        parsed = json.loads(cached)
                        if isinstance(parsed, list) and parsed:
                            logger.debug("Cache hit for {}", query_hash)
                            return [NewsItem(**item) for item in parsed]
                    except (json.JSONDecodeError, KeyError):
                        pass

        # Cache miss — fetch
        items = self._fetch_yfinance(ticker, market, shock_date)
        if not items:
            items = self._fetch_rss(ticker, market, shock_date)

        # Write to search_cache
        if self.db is not None and items:
            try:
                self.db.save_search_cache(
                    query_hash,
                    f"{market}:{ticker}:{shock_date}",
                    "yfinance" if items else "rss",
                    [item.to_dict() for item in items],
                )
            except Exception as exc:
                logger.warning(
                    "Failed to save search cache for {}: {}", query_hash, exc
                )

        return items

    # --- private helpers ---

    def _fetch_yfinance(
        self, ticker: str, market: str, shock_date: str
    ) -> List[NewsItem]:
        """Try yfinance.Ticker(...).news. Return empty list if no news available."""
        tk = ticker
        if market == "TW":
            tk = f"{ticker}.TW"
        try:
            yt = self.yfinance_module.Ticker(tk)
            news = getattr(yt, "news", [])
            if not news:
                return []
            items: List[NewsItem] = []
            for entry in news:
                if isinstance(entry, dict):
                    items.append(NewsItem(
                        title=entry.get("title", ""),
                        url=entry.get("link", ""),
                        body=entry.get("content", ""),
                        published_at=(
                            entry.get("providerPublishTime", "")
                            or entry.get("publishedAt", "")
                        ),
                    ))
            return items
        except Exception as exc:
            logger.warning("yfinance news failed for {}: {}", tk, exc)
            return []

    def _fetch_rss(
        self, ticker: str, market: str, shock_date: str
    ) -> List[NewsItem]:
        """Fallback: fetch RSS feed and filter by ticker name / date."""
        url = self.RSS_ENDPOINTS.get(market, "")
        if not url:
            return []

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            xml_text = resp.text
        except Exception as exc:
            logger.warning("RSS fetch failed for {}: {}", market, exc)
            return []

        # Minimal RSS parsing — extract <title>, <link>, <pubDate> from <item> blocks
        items: List[NewsItem] = []
        for block in re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL):
            title_match = re.search(r"<title>(.*?)</title>", block)
            link_match = re.search(r"<link>(.*?)</link>", block)
            pubdate_match = re.search(r"<pubDate>(.*?)</pubDate>", block)
            if title_match:
                title = title_match.group(1).strip()
                # Skip items that don't mention the ticker (simple substring)
                if ticker and ticker not in title:
                    continue
                items.append(NewsItem(
                    title=title,
                    url=(link_match.group(1) if link_match else ""),
                    published_at=(pubdate_match.group(1) if pubdate_match else ""),
                ))
        return items
