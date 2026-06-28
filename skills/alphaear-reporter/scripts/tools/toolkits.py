"""
AlphaEar 工具套件层 - Agno Toolkit 适配器
复用 utils 中的底层工具实现，提供 Agno Agent 兼容的 Toolkit 接口
"""
from datetime import datetime
from typing import Optional
from agno.tools import Toolkit
from loguru import logger

from ..utils.database_manager import DatabaseManager
from ..utils.news_tools import NewsNowTools, PolymarketTools
from ..utils.search_tools import SearchTools
from ..utils.sentiment_tools import SentimentTools


class NewsToolkit(Toolkit):
    """
    新闻工具套件 - 套件装 NewsNowTools 為 Agno Toolkit
    
    提供热点新闻取得、内容提取等功能
    """
    
    def __init__(self, db: DatabaseManager, **kwargs):
        self._news_tools = NewsNowTools(db)
        self._sources = self._news_tools.SOURCES
        
        tools = [
            self.fetch_hot_news,
            self.fetch_news_content,
            self.get_unified_trends,
            self.enrich_news_content,
        ]
        super().__init__(name="news_toolkit", tools=tools, **kwargs)


    def fetch_hot_news(self, source_id: str, count: int = 10) -> str:
        """
        从指定新闻源取得热点新闻列表。
        
        Args:
            source_id: 新闻源标识符。可选值按類別别:
                **金融類別**: "cls" (财联社), "wallstreetcn" (华尔街见闻), "xueqiu" (雪球)
                **綜合類別**: "weibo" (微博热搜), "zhihu" (知乎热榜), "baidu" (百度热搜),
                           "toutiao" (今日头条), "douyin" (抖音), "thepaper" (澎湃新闻)
                **科技類別**: "36kr" (36氪), "ithome" (IT之家), "v2ex", "juejin" (掘金),
                           "hackernews" (Hacker News)
                推荐金融分析使用 "cls", "wallstreetcn", "xueqiu"。
            count: 取得的新闻数量，預設 10 条。
        
        Returns:
            热点新闻列表的文本描述，套件含排名、标题和链接。如果源不可用则回傳錯誤信息。
        """
        logger.info(f"🔧 [TOOL CALLED] fetch_hot_news(source_id={source_id}, count={count})")
        
        items = self._news_tools.fetch_hot_news(source_id, count=count, fetch_content=False)
        
        if not items:
            return f"取得 {source_id} 热点失敗"
        
        source_name = self._sources.get(source_id, source_id)
        result = f"## {source_name} 热点 (取得時間: {datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        
        for item in items:
            result += f"{item['rank']}. {item['title']}\n   链接: {item['url']}\n\n"
        
        logger.info(f"✅ [TOOL SUCCESS] Got {len(items)} news items from {source_id}")
        return result

    def fetch_news_content(self, url: str) -> str:
        """
        使用 Jina Reader 抓取指定 URL 的网页正文内容。
        
        Args:
            url: 需要抓取内容的完整网页 URL，必须以 http:// 或 https:// 开头。
        
        Returns:
            提取的网页正文内容，如果失敗则回傳錯誤信息。
        """
        content = self._news_tools.fetch_news_content(url)
        if content:
            return content[:5000]  # 限制长度
        return "内容抓取失敗"

    def get_unified_trends(self, sources: str = "wallstreetcn,cls") -> str:
        """
        取得多平台綜合热点报告。
        
        Args:
            sources: 要扫描的新闻源，用逗号分隔。
                     可选值: weibo, zhihu, baidu, toutiao, wallstreetcn, cls
                     預設: "wallstreetcn,cls" (金融资讯)
        
        Returns:
            格式化的热点汇总报告。
        """
        source_list = [s.strip() for s in sources.split(",")]
        report = self._news_tools.get_unified_trends(source_list)
        return report

    def enrich_news_content(self, source: str = None, limit: int = 5) -> str:
        """
        為資料库中缺少正文内容的新闻补充内容。
        
        Args:
            source: 筛选特定新闻源（如 "cls"），為空则处理所有。
            limit: 最多处理的新闻数量，預設 5 条。
        
        Returns:
            处理结果的描述。
        """
        logger.info(f"🔧 [TOOL CALLED] enrich_news_content(source={source}, limit={limit})")
        
        # 取得需要补充内容的新闻
        news_items = self._news_tools.db.get_daily_news(source=source, limit=limit)
        items_without_content = [n for n in news_items if not n.get('content')]
        
        if not items_without_content:
            return "没有需要补充内容的新闻"
        
        updated_count = 0
        cursor = self._news_tools.db.conn.cursor()
        
        for item in items_without_content[:limit]:
            url = item.get('url')
            if url:
                content = self._news_tools.fetch_news_content(url)
                if content:
                    cursor.execute(
                        "UPDATE daily_news SET content = ? WHERE id = ?",
                        (content[:10000], item['id'])
                    )
                    updated_count += 1
        
        self._news_tools.db.conn.commit()
        logger.info(f"✅ [TOOL SUCCESS] Enriched {updated_count} news items with content")
        
        return f"✅ 已為 {updated_count} 条新闻补充正文内容"


class PolymarketToolkit(Toolkit):
    """
    Polymarket 预测市場工具套件 - 取得热门预测市場資料
    
    预测市場資料可反映公众情绪、预期和关注度
    """
    
    def __init__(self, db: DatabaseManager, **kwargs):
        self._poly_tools = PolymarketTools(db)
        
        tools = [
            self.get_prediction_markets,
            self.get_market_summary,
        ]
        super().__init__(name="polymarket_toolkit", tools=tools, **kwargs)
    
    def get_prediction_markets(self, limit: int = 20) -> str:
        """
        取得 Polymarket 活跃预测市場的关键資料。
        
        预测市場反映公众对重大事件的概率预期，可用于:
        - 分析市場情绪和風險偏好
        - 了解热门话题的关注度
        - 取得重大事件的概率预期
        
        Args:
            limit: 取得的市場数量，預設 20 个。
        
        Returns:
            预测市場資料列表，套件含问题、结果概率和交易量。
            如果取得失敗回傳錯誤信息。
        """
        logger.info(f"🔧 [TOOL CALLED] get_prediction_markets(limit={limit})")
        
        markets = self._poly_tools.get_active_markets(limit)
        if not markets:
            return "❌ 无法取得 Polymarket 資料（可能是網路问题）"
        
        result = f"## 🔮 Polymarket 热门预测 (共 {len(markets)} 个)\n\n"
        for i, m in enumerate(markets[:limit], 1):
            question = m.get("question", "Unknown")
            prices = m.get("outcomePrices", [])
            volume = m.get("volume", 0)
            
            result += f"{i}. **{question}**\n"
            if prices:
                result += f"   概率: {prices}\n"
            if volume:
                try:
                    result += f"   交易量: ${float(volume):,.0f}\n"
                except:
                    result += f"   交易量: {volume}\n"
            result += "\n"
        
        logger.info(f"✅ [TOOL SUCCESS] Got {len(markets)} prediction markets")
        return result
    
    def get_market_summary(self, limit: int = 10) -> str:
        """
        取得预测市場摘要报告，了解当前热门话题和公众预期。
        
        Args:
            limit: 取得的市場数量，預設 10 个。
            
        Returns:
            格式化的预测市場报告。
        """
        return self._poly_tools.get_market_summary(limit)


class SentimentToolkit(Toolkit):
    """
    情緒分析工具套件 - 套件装 SentimentTools 為 Agno Toolkit

    提供文本情緒存取功能（由 Agent 自行執行情緒分析）
    """

    def __init__(self, db: DatabaseManager, **kwargs):
        self._sentiment_tools = SentimentTools(db)
        self._db = db
        
        tools = [
            self.analyze_sentiment,
            self.batch_update_sentiment,
        ]
        super().__init__(name="sentiment_toolkit", tools=tools, **kwargs)

    def analyze_sentiment(self, text: str) -> str:
        """
        分析文本的情緒極性。

        Args:
            text: 需要分析的文本內容，如新聞標題或摘要。

        Returns:
            情緒分析結果，包含分值(-1.0到1.0)和標籤(positive/negative/neutral)。
        """
        result = self._sentiment_tools.analyze_sentiment(text)
        
        score = result.get('score', 0.0)
        label = result.get('label', 'neutral')
        reason = result.get('reason', '')
        
        return f"""情绪分析结果:
- 文本: {text[:100]}{'...' if len(text) > 100 else ''}
- 分值: {score:.2f}
- 標籤: {label}
- 分析: {reason}"""

    def batch_update_sentiment(self, source: str = None, limit: int = 20) -> str:
        """
        批量更新資料库中新闻的情绪分数。
        
        Args:
            source: 筛选特定新闻源（如 "cls", "wallstreetcn"），為空则处理所有。
            limit: 最多处理的新闻数量，預設 20 条。
        
        Returns:
            更新结果的描述。
        """
        logger.info(f"🔧 [TOOL CALLED] batch_update_sentiment(source={source}, limit={limit})")
        
        count = self._sentiment_tools.batch_update_news_sentiment(source=source, limit=limit)
        
        return f"✅ 已更新 {count} 条新闻的情绪分数"



class SearchToolkit(Toolkit):
    """
    搜尋工具套件 - 套件装 SearchTools 為 Agno Toolkit
    
    提供網路搜尋功能（支援 Jina、DuckDuckGo 和百度）
    
    当环境變數 JINA_API_KEY 設定時，預設使用 Jina Search，
    提供 LLM 友好的搜尋结果。
    """
    
    def __init__(self, db: DatabaseManager, **kwargs):
        self._search_tools = SearchTools(db)
        
        tools = [
            self.web_search,
            self.aggregate_search,
        ]
        super().__init__(name="search_toolkit", tools=tools, **kwargs)

    def web_search(self, query: str, engine: str = None, max_results: int = 5) -> str:
        """
        使用指定搜尋引擎执行網路搜尋。
        
        Args:
            query: 搜尋关键词，如 "英伟达财报" 或 "光伏行業政策"。
            engine: 搜尋引擎選擇。可选值: 
                    "jina" (Jina Search，需配置 JINA_API_KEY，LLM友好輸出),
                    "ddg" (DuckDuckGo，推荐英文/国际搜尋), 
                    "baidu" (百度，推荐中文/国内搜尋)。
                    預設: 若配置了 JINA_API_KEY 则使用 "jina"，否则 "ddg"。
            max_results: 回傳结果数量。預設 5。
        
        Returns:
            搜尋结果的文本描述。
        """
        return self._search_tools.search(query, engine=engine, max_results=max_results)

    def aggregate_search(self, query: str, max_results: int = 5) -> str:
        """
        同時使用多个搜尋引擎搜尋并聚合结果。
        
        Args:
            query: 搜尋关键词。
            max_results: 每个引擎回傳的最大结果数。預設 5。
        
        Returns:
            聚合后的搜尋结果。
        """
        return self._search_tools.aggregate_search(query, max_results=max_results)


class ContextSearchToolkit(Toolkit):
    """
    上下文搜尋工具套件 - 用于 RAG 场景的文档片段检索
    
    支援在内存中存储文档片段，并通过关键词搜尋相关内容。
    适用于 ReportAgent 的分段编辑场景。
    """
    
    def __init__(self, **kwargs):
        self._store = {}  # {doc_id: {"title": str, "content": str, "summary": str}}
        
        tools = [
            self.search_context,
            self.get_toc,
        ]
        super().__init__(name="context_search_toolkit", tools=tools, **kwargs)
    
    def add_document(self, doc_id: str, title: str, content: str, summary: str = ""):
        """添加文档到存储（供外部呼叫，非 LLM 工具）"""
        self._store[doc_id] = {
            "title": title,
            "content": content,
            "summary": summary or content[:200] + "..."
        }
        logger.info(f"📄 Added document to context store: {doc_id} - {title[:30]}...")
    
    def clear(self):
        """清空文档存储"""
        self._store.clear()
        logger.info("🗑️ Context store cleared")
    
    def search_context(self, query: str, max_results: int = 3) -> str:
        """
        在已存储的文档中搜尋与查询相关的内容片段。
        
        Args:
            query: 搜尋关键词，如 "消费板块" 或 "茅台 预测"。
            max_results: 回傳的最大结果数，預設 3。
        
        Returns:
            匹配的文档片段，按相关性排序。
        """
        logger.info(f"🔍 [TOOL CALLED] search_context(query={query}, max_results={max_results})")
        
        if not self._store:
            return "⚠️ 上下文存储為空，无可搜尋内容。"
        
        # 简单的关键词匹配 + 计分
        query_terms = query.lower().split()
        results = []
        
        for doc_id, doc in self._store.items():
            score = 0
            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()
            
            for term in query_terms:
                # 标题匹配權重更高
                if term in title_lower:
                    score += 3
                if term in content_lower:
                    score += content_lower.count(term)
            
            if score > 0:
                results.append((score, doc_id, doc))
        
        # 按分数排序
        results.sort(key=lambda x: x[0], reverse=True)
        results = results[:max_results]
        
        if not results:
            return f"未找到与 '{query}' 相关的内容。"
        
        output = f"## 搜尋结果 (查询: {query})\n\n"
        for score, doc_id, doc in results:
            output += f"### [{doc_id}] {doc['title']}\n"
            # 回傳摘要而非全文，节省 token
            output += f"{doc['summary']}\n\n"
        
        logger.info(f"✅ [TOOL SUCCESS] Found {len(results)} matching documents")
        return output
    
    def get_toc(self) -> str:
        """
        取得当前存储的所有文档的目录（TOC）。
        
        Returns:
            文档目录列表，套件含 ID 和标题。
        """
        logger.info("🔍 [TOOL CALLED] get_toc()")
        
        if not self._store:
            return "⚠️ 上下文存储為空。"
        
        output = "## 文档目录 (TOC)\n\n"
        for doc_id, doc in self._store.items():
            output += f"- **[{doc_id}]** {doc['title']}\n"
        
        return output

