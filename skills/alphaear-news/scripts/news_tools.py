import requests
from requests.exceptions import RequestException, Timeout
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from .database_manager import DatabaseManager
from .content_extractor import ContentExtractor

class NewsNowTools:
    """热点新闻取得工具 - 接入 NewsNow API 与 Jina 内容提取"""
    
    BASE_URL = "https://newsnow.busiyi.world"
    SOURCES = {
        # 金融類別
        "cls": "财联社",
        "wallstreetcn": "华尔街见闻",
        "xueqiu": "雪球热榜",
        # 綜合/社交
        "weibo": "微博热搜",
        "zhihu": "知乎热榜",
        "baidu": "百度热搜",
        "toutiao": "今日头条",
        "douyin": "抖音热榜",
        "thepaper": "澎湃新闻",
        # 科技類別
        "36kr": "36氪",
        "ithome": "IT之家",
        "v2ex": "V2EX",
        "juejin": "掘金",
        "hackernews": "Hacker News",
    }


    def __init__(self, db: DatabaseManager):
        self.db = db
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        self.extractor = ContentExtractor()
        # Simple in-memory cache: source_id -> {"time": timestamp, "data": []}
        self._cache = {}

    def fetch_hot_news(self, source_id: str, count: int = 15, fetch_content: bool = False) -> List[Dict]:
        """
        从指定新闻源取得热点新闻列表（支援5分鐘快取）。
        """
        # 1. Check cache validity (5 minutes)
        cache_key = f"{source_id}_{count}"
        cached = self._cache.get(cache_key)
        now = time.time()
        
        if cached and (now - cached["time"] < 300):
            logger.info(f"⚡ Using cached news for {source_id} (Age: {int(now - cached['time'])}s)")
            return cached["data"]

        try:
            url = f"{self.BASE_URL}/api/s?id={source_id}"
            response = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])[:count]
                processed_items = []
                for i, item in enumerate(items, 1):
                    item_url = item.get("url", "")
                    content = ""
                    if fetch_content and item_url:
                        content = self.extractor.extract_with_jina(item_url) or ""
                    
                    processed_items.append({
                        "id": item.get("id") or f"{source_id}_{int(time.time())}_{i}",
                        "source": source_id,
                        "rank": i,
                        "title": item.get("title", ""),
                        "url": item_url,
                        "content": content,
                        "publish_time": item.get("publish_time"),
                        "meta_data": item.get("extra", {})
                    })
                
                # Update Cache
                self._cache[cache_key] = {"time": now, "data": processed_items}
                logger.info(f"✅ Fetched and cached news for {source_id}")
                
                self.db.save_daily_news(processed_items)
                return processed_items
            else:
                logger.error(f"NewsNow API Error: {response.status_code}")
                # Fallback to stale cache if available
                if cached:
                    logger.warning(f"⚠️ API failed, using stale cache for {source_id}")
                    return cached["data"]
                return []
        except Timeout:
            logger.error(f"Timeout fetching hot news from {source_id}")
            if cached:
                logger.warning(f"⚠️ Timeout, using stale cache for {source_id}")
                return cached["data"]
            return []
        except RequestException as e:
            logger.error(f"Network error fetching hot news from {source_id}: {e}")
            if cached:
                 logger.warning(f"⚠️ Network check failed, using stale cache for {source_id}")
                 return cached["data"]
            return []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response from NewsNow for {source_id}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching hot news from {source_id}: {e}")
            return []

    def fetch_news_content(self, url: str) -> Optional[str]:
        """
        使用 Jina Reader 抓取指定 URL 的网页正文内容。
        
        Args:
            url: 需要抓取内容的完整网页 URL，必须以 http:// 或 https:// 开头。
        
        Returns:
            提取的网页正文内容 (Markdown 格式)，如果失敗则回傳 None。
        """
        return self.extractor.extract_with_jina(url)

    def get_unified_trends(self, sources: Optional[List[str]] = None) -> str:
        """
        取得多平台綜合热点报告，自動聚合多个新闻源的热门内容。
        
        Args:
            sources: 要扫描的新闻源列表。可选值按類別别:
                **金融類別**: "cls", "wallstreetcn", "xueqiu"
                **綜合類別**: "weibo", "zhihu", "baidu", "toutiao", "douyin", "thepaper"
                **科技類別**: "36kr", "ithome", "v2ex", "juejin", "hackernews"
        
        Returns:
            格式化的 Markdown 热点汇总报告，套件含各平台 Top 10 热点标题和链接。
        """
        sources = sources or ["weibo", "zhihu", "wallstreetcn"]
        all_news = []
        for src in sources:
            all_news.extend(self.fetch_hot_news(src))
            time.sleep(0.2)
        
        if not all_news:
            return "❌ 未能取得到热点資料"
            
        report = f"# 即時全网热点汇总 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        for src in sources:

            src_name = self.SOURCES.get(src, src)
            report += f"### 🔥 {src_name}\n"
            src_news = [n for n in all_news if n['source'] == src]
            for n in src_news[:10]:
                report += f"- {n['title']} ([链接]({n['url']}))\n"
            report += "\n"
            
        return report


class PolymarketTools:
    """Polymarket 预测市場資料工具 - 取得热门预测市場反映公众情绪和预期"""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    
    def get_active_markets(self, limit: int = 20) -> List[Dict]:
        """
        取得活跃的预测市場，用于分析公众情绪和预期。
        
        预测市場資料可以反映:
        - 公众对重大事件的预期概率
        - 市場情绪和風險偏好
        - 热门话题的关注度
        
        Args:
            limit: 取得的市場数量，預設 20 个。
        
        Returns:
            套件含预测市場信息的列表，每个市場套件含:
            - question: 预测问题
            - outcomes: 可能的结果
            - outcomePrices: 各结果的概率价格
            - volume: 交易量
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/markets",
                params={"active": "true", "closed": "false", "limit": limit},
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                markets = response.json()
                result = []
                for m in markets:
                    result.append({
                        "id": m.get("id"),
                        "question": m.get("question"),
                        "slug": m.get("slug"),
                        "outcomes": m.get("outcomes"),
                        "outcomePrices": m.get("outcomePrices"),
                        "volume": m.get("volume"),
                        "liquidity": m.get("liquidity"),
                    })
                logger.info(f"✅ 取得 {len(result)} 个预测市場")
                return result
            else:
                logger.warning(f"⚠️ Polymarket API 回傳 {response.status_code}")
                return []
        except Timeout:
            logger.error("Timeout fetching Polymarket markets")
            return []
        except RequestException as e:
            logger.error(f"Network error fetching Polymarket markets: {e}")
            return []
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from Polymarket")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching Polymarket markets: {e}")
            return []
    
    def get_market_summary(self, limit: int = 10) -> str:
        """
        取得预测市場摘要报告，用于了解当前热门话题和公众预期。
        
        Args:
            limit: 取得的市場数量
            
        Returns:
            格式化的预测市場报告
        """
        markets = self.get_active_markets(limit)
        if not markets:
            return "❌ 无法取得 Polymarket 資料"
        
        report = f"# 🔮 Polymarket 热门预测 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        for i, m in enumerate(markets, 1):
            question = m.get("question", "Unknown")
            prices = m.get("outcomePrices", [])
            volume = m.get("volume", 0)
            
            report += f"**{i}. {question}**\n"
            if prices:
                report += f"   概率: {prices}\n"
            if volume:
                report += f"   交易量: ${float(volume):,.0f}\n"
            report += "\n"
        
        return report
