"""
AlphaEar 工具套件层 - Agno Toolkit 适配器
复用 utils 中的底层工具实现，提供 Agno Agent 兼容的 Toolkit 接口
"""
from datetime import datetime
from typing import Optional
from agno.tools import Toolkit
from loguru import logger

from ..utils.database_manager import DatabaseManager
from ..utils.news_tools import NewsFetcher, PolymarketTools
from ..utils.search_tools import SearchTools
from ..utils.sentiment_tools import SentimentTools


class NewsToolkit(Toolkit):
    """
    新闻工具套件 - 套件装 NewsFetcher 為 Agno Toolkit

    提供財經新闻取得（RSS 来源）、Polymarket 预测市場等功能
    """

    def __init__(self, db: DatabaseManager, **kwargs):
        self._news_tools = NewsFetcher(db)
        self._sources = self._news_tools.SOURCES

        tools = [
            self.fetch_hot_news,
            self.get_unified_trends,
        ]
        super().__init__(name="news_toolkit", tools=tools, **kwargs)

    def fetch_hot_news(self, source_id: str, count: int = 10) -> str:
        """
        从指定新闻源取得最新新闻。

        Args:
            source_id: 新闻源标识符。有效值:
                **台湾財經**: "cna_finance" (中央社財經), "cna_tech" (中央社科技)
                **日本经济**: "nhk_economy" (NHK经济)
                **美股/全球**: "bloomberg" (Bloomberg Markets), "investing_reuters" (Reuters)
            count: 取得的数量，预设 10 笔。

        Returns:
            新闻列表的文本描述，含排名、标题和连结。
        """
        logger.info(f"\ud83d\udd27 [TOOL CALLED] fetch_hot_news(source_id={source_id}, count={count})")

        items = self._news_tools.fetch_hot_news(source_id, count=count)

        if not items:
            return f"取得 {source_id} 新闻失敗"

        source_obj = self._sources.get(source_id)
        source_name = source_obj.name if source_obj else source_id
        result = f"## {source_name} 新闻 (取得時間: {datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"

        for item in items:
            result += f"{item['rank']}. {item['title']}\n   连结: {item['url']}\n\n"

        logger.info(f"\u2705 [TOOL SUCCESS] Got {len(items)} news items from {source_id}")
        return result

    def get_unified_trends(self, sources: str = "cna_finance,bloomberg") -> str:
        """
        取得多平台綜合新闻报告。

        Args:
            sources: 要扫描的新闻源，用逗号分隔。
                     有效值: cna_finance, cna_tech, nhk_economy, bloomberg, investing_reuters
                     预设: "cna_finance,bloomberg" (台湾財經 + 美股)

        Returns:
            格式化的新闻彙整报告。
        """
        source_list = [s.strip() for s in sources.split(",")]
        report = self._news_tools.get_unified_trends(source_list)
        return report


class PolymarketToolkit(Toolkit):
    """
    Polymarket 预测市場工具套件 - 取得热门预测市場资料

    预测市場资料可反映公众情绪、预期和关注度
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
        取得 Polymarket 活跃预测市場的关键资料。

        预测市場反映公众对重大事件的概率预期，可用于:
        - 分析市場情绪和風險偏好
        - 了解热门话题的关注度
        - 取得重大事件的概率预期

        Args:
            limit: 取得的市場数量，预设 20 个。

        Returns:
            预测市場资料列表，含问题、结果概率和交易量。
        """
        logger.info(f"\ud83d\udd27 [TOOL CALLED] get_prediction_markets(limit={limit})")

        markets = self._poly_tools.get_active_markets(limit)
        if not markets:
            return "\u274c 无法取得 Polymarket 资料（可能是网路问题）"

        result = f"## \ud83d\udd2e Polymarket 热门预测 (共 {len(markets)} 个)\n\n"
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
                except Exception:
                    result += f"   交易量: {volume}\n"
            result += "\n"

        logger.info(f"\u2705 [TOOL SUCCESS] Got {len(markets)} prediction markets")
        return result

    def get_market_summary(self, limit: int = 10) -> str:
        """
        取得预测市場摘要报告，了解当前热门话题和公众预期。

        Args:
            limit: 取得的市場数量，预设 10 个。

        Returns:
            格式化的预测市場报告。
        """
        return self._poly_tools.get_market_summary(limit)


class SentimentToolkit(Toolkit):
    """
    情绪分析工具套件 - 套件装 SentimentTools 為 Agno Toolkit

    提供文本情绪存取功能（由 Agent 自行执行情绪分析）
    """

    def __init__(self, db: DatabaseManager, **kwargs):
        self._sentiment_tools = SentimentTools(db)
        self._db = db

        tools = [
            self.batch_update_sentiment,
        ]
        super().__init__(name="sentiment_toolkit", tools=tools, **kwargs)

    def batch_update_sentiment(self, source: str = None, limit: int = 20) -> str:
        """
        批量更新資料库中新闻的情绪分数。

        Args:
            source: 筛选特定新闻源（如 "cna_finance", "bloomberg"），為空则处理所有。
            limit: 最多处理的新闻数量，预设 20 条。

        Returns:
            更新结果的描述。
        """
        logger.info(f"\ud83d\udd27 [TOOL CALLED] batch_update_sentiment(source={source}, limit={limit})")

        count = self._sentiment_tools.batch_update_news_sentiment(source=source, limit=limit)

        return f"\u2705 已更新 {count} 条新闻的情绪分数"


class SearchToolkit(Toolkit):
    """
    搜寻工具套件 - 套件装 SearchTools 為 Agno Toolkit

    提供网路搜寻功能（支援 Jina、DuckDuckGo 和百度）

    当环境變數 JINA_API_KEY 设定時時，预设使用 Jina Search，
    提供 LLM 友好的搜寻结果。
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
        使用指定搜寻引擎执行网路搜寻。

        Args:
            query: 搜寻关键词，如 "英伟达财报" 或 "光伏行業政策"。
            engine: 搜寻引擎選擇。可选值:
                    "jina" (Jina Search，需配置 JINA_API_KEY，LLM友好輸出),
                    "ddg" (DuckDuckGo，推荐英文/国际搜寻),
                    "baidu" (百度，推荐中文/国内搜寻)。
                    预设: 若配置了 JINA_API_KEY 则使用 "jina"，否则 "ddg"。
            max_results: 回报结果数量。预设 5。

        Returns:
            搜寻结果的文本描述。
        """
        return self._search_tools.search(query, engine=engine, max_results=max_results)

    def aggregate_search(self, query: str, max_results: int = 5) -> str:
        """
        同時使用多个搜寻引擎搜寻并聚合结果。

        Args:
            query: 搜寻关键词。
            max_results: 每个引擎回报的最大结果数。预设 5。

        Returns:
            聚合后的搜寻结果。
        """
        return self._search_tools.aggregate_search(query, max_results=max_results)


class ContextSearchToolkit(Toolkit):
    """
    上下文搜寻工具套件 - 用于 RAG 场景的文档片段检索

    支援在内存中存储文档片段，并通过关键词搜寻相关内容。
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
        logger.info(f"\ud83d\udcc4 Added document to context store: {doc_id} - {title[:30]}...")

    def clear(self):
        """清空文档存储"""
        self._store.clear()
        logger.info("\ud83d\uddd1\ufe0f Context store cleared")

    def search_context(self, query: str, max_results: int = 3) -> str:
        """
        在已存储的文档中搜寻与查询相关的内容片段。

        Args:
            query: 搜寻关键词，如 "消费板块" 或 "茅台 预测"。
            max_results: 回报的最大结果数，预设 3。

        Returns:
            匹配的文档片段，按相关性排序。
        """
        logger.info(f"\ud83d\udd0d [TOOL CALLED] search_context(query={query}, max_results={max_results})")

        if not self._store:
            return "\u26a0\ufe0f 上下文存储為空，无可搜寻内容。"

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

        output = f"## 搜寻结果 (查询: {query})\n\n"
        for score, doc_id, doc in results:
            output += f"### [{doc_id}] {doc['title']}\n"
            # 回报摘要而非全文，节省 token
            output += f"{doc['summary']}\n\n"

        logger.info(f"\u2705 [TOOL SUCCESS] Found {len(results)} matching documents")
        return output

    def get_toc(self) -> str:
        """
        取得当前存储的所有文档的目录（TOC）。

        Returns:
            文档目录列表，含 ID 和标题。
        """
        logger.info("\ud83d\udd0d [TOOL CALLED] get_toc()")

        if not self._store:
            return "\u26a0\ufe0f 上下文存储為空。"

        output = "## 文档目录 (TOC)\n\n"
        for doc_id, doc in self._store.items():
            output += f"- **[{doc_id}]** {doc['title']}\n"

        return output
