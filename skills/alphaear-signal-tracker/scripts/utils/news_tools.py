import requests
from requests.exceptions import RequestException, Timeout
import feedparser
import json
import re
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from loguru import logger
from .database_manager import DatabaseManager


class RSSFeedSource:
    """RSS 來源設定"""

    def __init__(
        self,
        source_id: str,
        name: str,
        url: str,
        language: str = "unknown",
        max_hours: int = 24,
    ):
        self.source_id = source_id
        self.name = name
        self.url = url
        self.language = language
        self.max_hours = max_hours


class NewsFetcher:
    """從 RSS Feed 抓取財經新聞，並持久化到本機資料庫。

    支援台灣（中央社）、日本（NHK）、美國/全球（Bloomberg、Reuters via Investing.com）來源。
    實作時間窗口過濾（預設 24 小時）與 URL 去重，防止資料無限增長。
    """

    SOURCES = {
        "cna_finance": RSSFeedSource(
            source_id="cna_finance",
            name="中央社財經",
            url="https://feeds.feedburner.com/rsscna/finance",
            language="zh-TW",
        ),
        "cna_tech": RSSFeedSource(
            source_id="cna_tech",
            name="中央社科技",
            url="https://feeds.feedburner.com/rsscna/technology",
            language="zh-TW",
        ),
        "nhk_economy": RSSFeedSource(
            source_id="nhk_economy",
            name="NHK 經濟",
            url="https://news.web.nhk/n-data/conf/na/rss/cat5.xml",
            language="ja",
        ),
        "bloomberg": RSSFeedSource(
            source_id="bloomberg",
            name="Bloomberg Markets",
            url="https://feeds.bloomberg.com/markets/news.rss",
            language="en",
        ),
        "investing_reuters": RSSFeedSource(
            source_id="investing_reuters",
            name="Reuters (via Investing.com)",
            url="https://www.investing.com/rss/news.rss",
            language="en",
        ),
    }

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(self, db: DatabaseManager):
        self.db = db
        # 記憶體快取：source_id -> {"time": timestamp, "data": [...]}
        self._cache: Dict[str, Dict] = {}

    def _normalize_rss_item(self, entry, source: RSSFeedSource) -> Optional[Dict]:
        """將單一 RSS <item>/<entry> 轉為標準新聞 dict"""
        title = getattr(entry, "title", "").strip()
        if not title:
            return None

        # 取得連結（優先 link，fallback guid）
        link = getattr(entry, "link", "") or getattr(entry, "guid", "")
        link = link.strip() if link else ""
        if not link:
            return None

        # 取得描述 / 摘要
        summary = ""
        for attr in ("summary", "description", "content"):
            content = getattr(entry, attr, None)
            if content:
                if hasattr(content, "get"):
                    summary = content.get("value", "")
                else:
                    summary = str(content)
                break
        # 清除 HTML tag
        summary = self._strip_html(summary)

        # 取得發布時間
        publish_time = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6])
                publish_time = dt.isoformat()
            except Exception:
                pass
        elif hasattr(entry, "published"):
            publish_time = entry.published

        # 時間窗口過濾
        if publish_time:
            cutoff = datetime.now() - timedelta(hours=source.max_hours)
            try:
                pub_dt = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt < cutoff.astimezone(pub_dt.tzinfo if pub_dt.tzinfo else timezone.utc):
                    return None
            except Exception:
                pass

        # 用 URL + title 產生穩定 ID
        id_source = f"{source.source_id}:{link}:{title}"
        news_id = hashlib.sha256(id_source.encode()).hexdigest()[:16]

        return {
            "id": news_id,
            "source": source.source_id,
            "rank": 0,
            "title": title,
            "url": link,
            "content": summary,
            "publish_time": publish_time,
            "meta_data": {"language": source.language, "feed_name": source.name},
        }

    @staticmethod
    def _strip_html(text: str) -> str:
        """清除基本 HTML tag"""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&apos;", "'")
        return text.strip()

    def fetch_hot_news(
        self, source_id: str, count: int = 15, fetch_content: bool = False
    ) -> List[Dict]:
        """
        從單一 RSS 來源抓取近期新聞。

        Args:
            source_id: SOURCES 的 key（例如 'cna_finance'）。
            count: 回傳最大筆數。
            fetch_content: 目前不使用（RSS 的 summary 已是內容摘要）。

        Returns:
            標準化新聞 dict 列表。
        """
        source = self.SOURCES.get(source_id)
        if not source:
            logger.error(
                f"Unknown source_id: {source_id}. Available: {list(self.SOURCES.keys())}"
            )
            return []

        # 5 分鐘快取
        cache_key = source_id
        cached = self._cache.get(cache_key)
        now = time.time()
        if cached and (now - cached["time"] < 300):
            logger.info(f"Using cached news for {source_id} (Age: {int(now - cached['time'])}s)")
            items = cached["data"][:count]
            for i, item in enumerate(items, 1):
                item["rank"] = i
            return items

        try:
            logger.info(f"Fetching RSS feed: {source.name} ({source_id})")
            feed = feedparser.parse(source.url)

            if feed.bozo and not feed.entries:
                logger.warning(f"RSS parse error for {source_id}: {feed.bozo_exception}")
                if cached:
                    items = cached["data"][:count]
                    for i, item in enumerate(items, 1):
                        item["rank"] = i
                    return items
                return []

            processed = []
            for entry in feed.entries:
                item = self._normalize_rss_item(entry, source)
                if item:
                    processed.append(item)

            # 更新快取
            self._cache[cache_key] = {"time": now, "data": processed}
            logger.info(f"Fetched {len(processed)} items from {source_id}")

            # 存入 DB（含去重）
            saved = self.db.save_daily_news(processed)
            logger.info(f"Saved {saved} new/updated items to DB from {source_id}")

            # 回傳受限 + 排名
            result = processed[:count]
            for i, item in enumerate(result, 1):
                item["rank"] = i
            return result

        except Timeout:
            logger.error(f"Timeout fetching RSS: {source_id}")
        except RequestException as e:
            logger.error(f"Network error fetching RSS: {source_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching RSS: {source_id}: {e}")

        # Fallback 到舊快取
        if cached:
            logger.warning(f"Fetch failed, using stale cache for {source_id}")
            items = cached["data"][:count]
            for i, item in enumerate(items, 1):
                item["rank"] = i
            return items
        return []

    def fetch_all_sources(
        self, sources: Optional[List[str]] = None, count: int = 15
    ) -> List[Dict]:
        """
        一次從多個來源抓取新聞。

        Args:
            sources: 要抓取的 source_id 列表。預設全部。
            count: 每個來源最大筆數。

        Returns:
            所有來源合併的新聞列表。
        """
        sources = sources or list(self.SOURCES.keys())
        all_news = []
        for src in sources:
            all_news.extend(self.fetch_hot_news(src, count=count))
            time.sleep(0.3)  # 避開 rate limit
        return all_news

    def get_unified_trends(
        self, sources: Optional[List[str]] = None, count: int = 10
    ) -> str:
        """
        產生 Markdown 格式的新聞彙整報告。

        Args:
            sources: 要納入的來源 ID。預設全部。
            count: 每個來源在報告中的筆數。

        Returns:
            格式化 Markdown 字串。
        """
        sources = sources or list(self.SOURCES.keys())
        all_news = []
        for src in sources:
            all_news.extend(self.fetch_hot_news(src, count=count))
            time.sleep(0.3)

        if not all_news:
            return "無法取得新聞資料"

        report = f"# 即時財經新聞彙整 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        for src in sources:
            src_name = self.SOURCES[src].name if src in self.SOURCES else src
            src_news = [n for n in all_news if n["source"] == src]
            if not src_news:
                continue
            report += f"## {src_name}\n"
            for n in src_news[:count]:
                report += f"- {n['title']} ([原文]({n['url']}))\n"
            report += "\n"

        return report


class PolymarketTools:
    """Polymarket 預測市場資料工具"""

    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    def get_active_markets(self, limit: int = 20) -> List[Dict]:
        """
        取得活躍預測市場，用於分析公眾情緒與預期。

        預測市場資料反映:
        - 公眾對重大事件的預期機率
        - 市場情緒和風險偏好
        - 熱門話題的關注度

        Args:
            limit: 取得的市場數量，預設 20 個。

        Returns:
            套件含預測市場資訊的列表，每個市場套件含 question、outcomes、
            outcomePrices、volume、liquidity。
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/markets",
                params={"active": "true", "closed": "false", "limit": limit},
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                timeout=30,
            )

            if response.status_code == 200:
                markets = response.json()
                result = []
                for m in markets:
                    result.append(
                        {
                            "id": m.get("id"),
                            "question": m.get("question"),
                            "slug": m.get("slug"),
                            "outcomes": m.get("outcomes"),
                            "outcomePrices": m.get("outcomePrices"),
                            "volume": m.get("volume"),
                            "liquidity": m.get("liquidity"),
                        }
                    )
                logger.info(f"取得 {len(result)} 個預測市場")
                return result
            else:
                logger.warning(f"Polymarket API 回傳 {response.status_code}")
                return []

        except Timeout:
            logger.error("Timeout fetching Polymarket markets")
        except RequestException as e:
            logger.error(f"Network error fetching Polymarket markets: {e}")
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from Polymarket")
        except Exception as e:
            logger.error(f"Unexpected error fetching Polymarket markets: {e}")

        return []

    def get_market_summary(self, limit: int = 10) -> str:
        """
        產生 Polymarket 摘要報告。

        Args:
            limit: 報告中的市場數量。

        Returns:
            格式化 Markdown 字串。
        """
        markets = self.get_active_markets(limit)
        if not markets:
            return "無法取得 Polymarket 資料"

        report = f"Polymarket 熱門預測 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        for i, m in enumerate(markets, 1):
            question = m.get("question", "Unknown")
            prices = m.get("outcomePrices", [])
            volume = m.get("volume", 0)

            report += f"{i}. **{question}**\n"
            if prices:
                report += f"   機率: {prices}\n"
            if volume:
                report += f"   交易量: ${float(volume):,.0f}\n"
            report += "\n"

        return report
