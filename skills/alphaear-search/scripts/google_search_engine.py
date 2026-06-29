"""Google 搜尋引擎 — 透過 Jina Reader 包裝 Google 搜尋結果。

使用 s.jina.ai 的 Jina Search API 獲取 LLM-friendly 的搜尋結果。
"""

import os
import time
import threading
import urllib.parse
from typing import List, Dict
import requests
from loguru import logger


class GoogleSearchEngine:
    """Google 搜尋引擎封裝 — 使用 Jina Search (s.jina.ai) 進行搜尋。

    回傳 LLM 友好的結構化結果，格式與 JinaSearchEngine 一致。
    """

    JINA_SEARCH_URL = "https://s.jina.ai/"

    # 速率限制配置
    _rate_limit_no_key = 10
    _rate_window = 60.0
    _min_interval = 2.0
    _request_times: List[float] = []
    _last_request_time = 0.0
    _lock = threading.Lock()

    def __init__(self):
        self.api_key = os.getenv("JINA_API_KEY", "").strip()
        self.has_api_key = bool(self.api_key)
        if self.has_api_key:
            logger.info("✅ Google Search Engine (via Jina) ready")

    @classmethod
    def _wait_for_rate_limit(cls, has_api_key: bool) -> None:
        """等待以滿足速率限制"""
        if has_api_key:
            time.sleep(0.3)
            return

        with cls._lock:
            current_time = time.time()
            cls._request_times = [
                t for t in cls._request_times
                if current_time - t < cls._rate_window
            ]

            if len(cls._request_times) >= cls._rate_limit_no_key:
                oldest = cls._request_times[0]
                wait_time = cls._rate_window - (current_time - oldest) + 1.0
                if wait_time > 0:
                    logger.warning(f"⏳ Rate limit, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    current_time = time.time()
                    cls._request_times = [
                        t for t in cls._request_times
                        if current_time - t < cls._rate_window
                    ]

            time_since_last = current_time - cls._last_request_time
            if time_since_last < cls._min_interval:
                time.sleep(cls._min_interval - time_since_last)

            cls._request_times.append(time.time())
            cls._last_request_time = time.time()

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """執行搜尋。

        Args:
            query: 搜尋關鍵詞
            max_results: 回傳結果數量

        Returns:
            搜尋結果列表，每個結果包含 title, url, content
        """
        if not query:
            return []

        logger.info(f"🔍 Google Search (via Jina): {query}")

        self._wait_for_rate_limit(self.has_api_key)

        headers = {
            "Accept": "application/json",
            "X-Retain-Images": "none",
        }

        if self.has_api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            encoded_query = urllib.parse.quote(query)
            url = f"{self.JINA_SEARCH_URL}{encoded_query}"

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 429:
                logger.warning("⚠️ Rate limited (429), waiting 30s...")
                time.sleep(30)
                return self.search(query, max_results)

            if response.status_code != 200:
                logger.warning(f"Search failed (Status {response.status_code})")
                return []

            try:
                data = response.json()
            except Exception:
                return []

            results: List[Dict] = []
            items = data.get("data", []) if isinstance(data, dict) else data
            if not isinstance(items, list):
                items = [items] if items else []

            for i, item in enumerate(items[:max_results]):
                if isinstance(item, dict):
                    results.append({
                        "title": item.get("title", f"Result {i+1}"),
                        "url": item.get("url", ""),
                        "href": item.get("url", ""),
                        "content": item.get("content", item.get("description", "")),
                        "body": item.get("content", item.get("description", "")),
                    })
                elif isinstance(item, str):
                    results.append({
                        "title": f"Result {i+1}",
                        "url": "",
                        "content": item,
                    })

            logger.info(f"✅ Google Search returned {len(results)} results")
            return results

        except requests.exceptions.Timeout:
            logger.error("Search timeout")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Search request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Search unexpected error: {e}")
            return []
