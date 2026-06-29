import os

import hashlib

import json

import re

import requests

import time

import threading

from typing import List, Dict, Optional, Any

from agno.tools.duckduckgo import DuckDuckGoTools

from agno.tools.baidusearch import BaiduSearchTools

from datetime import datetime

from loguru import logger

from .database_manager import DatabaseManager

from .content_extractor import ContentExtractor

from .hybrid_search import LocalNewsSearch

from .google_search_engine import GoogleSearchEngine



# 預設搜尋快取 TTL（秒），可透過環境變數覆蓋

DEFAULT_SEARCH_TTL = int(os.getenv("SEARCH_CACHE_TTL", "3600"))  # 預設 1 小時



# 市場偵測正則表達式

US_TICKER_RE = re.compile(r'\b[A-Z]{2,5}\b')

TW_TICKER_RE = re.compile(r'\b\d{4}\b')



# 台股公司名稱關鍵字

TW_COMPANY_KEYWORDS = [
    '台積電', '聯發科', '鴻海', '台達電', '富邦金', '兆豐金',
    '國泰金', '中華電', '台塑', '南亞', '中鋼', '廣達',
    '聯電', '日月光', '統一', '大立光', '華碩', '和碩',
]



# 美股公司名稱關鍵字

US_COMPANY_KEYWORDS = [
    '蘋果', '英偉達', '微軟', '特斯拉', '谷歌', '亞馬遜',
    'Meta', 'NVIDIA', 'Apple', 'Microsoft', 'Tesla',
    'Google', 'Amazon', 'AMD', 'Intel', 'Netflix',
]





class JinaSearchEngine:

    """Jina Search API 封裝 - 使用 s.jina.ai 進行網路搜尋"""

    

    JINA_SEARCH_URL = "https://s.jina.ai/"

    

    # 速率限制配置

    _rate_limit_no_key = 10  # 無 key 時每分鐘最大請求數

    _rate_window = 60.0

    _min_interval = 2.0

    _request_times = []

    _last_request_time = 0.0

    _lock = threading.Lock()

    

    def __init__(self):

        self.api_key = os.getenv("JINA_API_KEY", "").strip()

        self.has_api_key = bool(self.api_key)

        if self.has_api_key:

            logger.info("✅ Jina Search API key configured")

    

    @classmethod

    def _wait_for_rate_limit(cls, has_api_key: bool) -> None:

        """等待以滿足速率限制"""

        if has_api_key:

            time.sleep(0.3)

            return

        

        with cls._lock:

            current_time = time.time()

            cls._request_times = [t for t in cls._request_times if current_time - t < cls._rate_window]

            

            if len(cls._request_times) >= cls._rate_limit_no_key:

                oldest = cls._request_times[0]

                wait_time = cls._rate_window - (current_time - oldest) + 1.0

                if wait_time > 0:

                    logger.warning(f"⏳ Jina Search rate limit, waiting {wait_time:.1f}s...")

                    time.sleep(wait_time)

                    current_time = time.time()

                    cls._request_times = [t for t in cls._request_times if current_time - t < cls._rate_window]

            

            time_since_last = current_time - cls._last_request_time

            if time_since_last < cls._min_interval:

                time.sleep(cls._min_interval - time_since_last)

            

            cls._request_times.append(time.time())

            cls._last_request_time = time.time()

    

    def search(self, query: str, max_results: int = 5) -> List[Dict]:

        """

        使用 Jina Search API 執行搜尋

        

        Args:

            query: 搜尋關鍵詞

            max_results: 回傳結果數量

            

        Returns:

            搜尋結果列表，每個結果套件含 title, url, content

        """

        if not query:

            return []

        

        logger.info(f"🔍 Jina Search: {query}")

        

        # 等待速率限制

        self._wait_for_rate_limit(self.has_api_key)

        

        headers = {

            "Accept": "application/json",

            "X-Retain-Images": "none",

        }

        

        if self.has_api_key:

            headers["Authorization"] = f"Bearer {self.api_key}"

        

        try:

            # Jina Search API: https://s.jina.ai/{query}

            import urllib.parse

            encoded_query = urllib.parse.quote(query)

            url = f"{self.JINA_SEARCH_URL}{encoded_query}"

            

            response = requests.get(url, headers=headers, timeout=30)

            

            if response.status_code == 429:

                logger.warning("⚠️ Jina Search rate limited (429), waiting 30s...")

                time.sleep(30)

                return self.search(query, max_results)

            

            if response.status_code != 200:

                logger.warning(f"Jina Search failed (Status {response.status_code})")

                return []

            

            # 解析回應

            try:

                data = response.json()

            except json.JSONDecodeError:

                # 如果回傳純文字，嘗試解析

                data = {"data": [{"title": "Search Result", "url": "", "content": response.text}]}

            

            results = []

            

            # Jina 回傳格式可能是 {"data": [...]} 或直接是列表

            items = data.get("data", []) if isinstance(data, dict) else data

            if not isinstance(items, list):

                items = [items] if items else []

            

            for i, item in enumerate(items[:max_results]):

                if isinstance(item, dict):

                    results.append({

                        "title": item.get("title", f"Result {i+1}"),

                        "url": item.get("url", ""),

                        "href": item.get("url", ""),  # 相容性

                        "content": item.get("content", item.get("description", "")),

                        "body": item.get("content", item.get("description", "")),  # 相容性

                    })

                elif isinstance(item, str):

                    results.append({

                        "title": f"Result {i+1}",

                        "url": "",

                        "content": item

                    })

            

            logger.info(f"✅ Jina Search returned {len(results)} results")

            return results

            

        except requests.exceptions.Timeout:

            logger.error("Jina Search timeout")

            return []

        except requests.exceptions.RequestException as e:

            logger.error(f"Jina Search request error: {e}")

            return []

        except Exception as e:

            logger.error(f"Jina Search unexpected error: {e}")

            return []



class SearchTools:

    """擴充套件性搜尋工具庫 - 支援多引擎聚合與內容快取"""

    

    def __init__(self, db: DatabaseManager):

        self.db = db

        

        # 檢查 Jina API Key 是否配置（Google 引擎共用）

        jina_api_key = os.getenv("JINA_API_KEY", "").strip()

        self._jina_enabled = bool(jina_api_key)



        self._engines = {

            "ddg": DuckDuckGoTools(),

            "baidu": BaiduSearchTools(),

            "local": LocalNewsSearch(db)

        }



        # 如果配置了 Jina API Key，新增 Jina 引擎

        if self._jina_enabled:

            self._engines["jina"] = JinaSearchEngine()

            logger.info("🚀 Jina Search engine enabled (JINA_API_KEY configured)")

            self._engines["google"] = GoogleSearchEngine()

            logger.info("🚀 Google Search engine enabled (via Jina)")



        # 確定預設搜尋引擎

        self._default_engine = "jina" if self._jina_enabled else "ddg"



    def _generate_hash(self, query: str, engine: str, max_results: int) -> str:

        return hashlib.md5(f"{engine}:{query}:{max_results}".encode()).hexdigest()



    def _detect_market(self, query: str) -> Optional[str]:

        """根據查詢內容自動偵測市場類型。"""

        if not query:

            return None

        if TW_TICKER_RE.search(query):

            return "tw"

        for keyword in TW_COMPANY_KEYWORDS:

            if keyword in query:

                return "tw"

        if US_TICKER_RE.search(query):

            return "us"

        for keyword in US_COMPANY_KEYWORDS:

            if keyword in query:

                return "us"

        return None



    def _select_engine(self, market: Optional[str]) -> str:

        """根據市場類型選擇適搜尋引擎。"""

        if market == "us":

            return "jina" if self._jina_enabled else "ddg"

        elif market == "tw":

            return "google" if self._jina_enabled else "ddg"

        else:

            return self._default_engine



    def search(self, query: str, engine: str = None, max_results: int = 5, ttl: Optional[int] = None, market: Optional[str] = None) -> str:

        """

        使用指定搜尋引擎執行網路搜尋，結果會被快取以提高效率。



        Args:

            query: 搜尋關鍵詞，如 "英偉達財報" 或 "光伏行業政策"。

            engine: 搜尋引擎選擇。可選值:

                    "jina" (Jina Search，需配置 JINA_API_KEY，LLM友好輸出),

                    "ddg" (DuckDuckGo，推薦英文/國際搜尋),

                    "baidu" (百度，推薦中文/國內搜尋),

                    "local" (本機歷史新聞搜尋，基於向量+BM25)。

                    預設: 若未指定 engine 且提供 market，則依市場自動選擇；

                    否則若配置了 JINA_API_KEY 則使用 "jina"，否則 "ddg"。

            max_results: 期望回傳的結果數量，預設 5 條。

            ttl: 快取有效期（秒）。如果快取超過此時間會重新搜尋。

                 預設使用環境變數 SEARCH_CACHE_TTL 或 3600 秒。

                 設為 0 可強制重新整理。

            market: 市場類型，可選 "us"、"tw"。若未指定且 engine 為 None，

                    會根據 query 自動偵測。



        Returns:

            搜尋結果的文字描述，套件含標題、摘要和連結。

        """

        # 使用預設引擎（如果配置了 Jina 則優先使用 Jina）

        if engine is None:

            detected_market = self._detect_market(query) if market is None else market

            engine = self._select_engine(detected_market)

        

        if engine not in self._engines:

            return f"Error: Unsupported engine '{engine}'. Available: {list(self._engines.keys())}"



        query_hash = self._generate_hash(query, engine, max_results)

        effective_ttl = ttl if ttl is not None else DEFAULT_SEARCH_TTL

        

        # 1. 嘗試從快取讀取 (local 引擎不快取，因為它本身就是查庫)

        if engine != "local":

            cache = self.db.get_search_cache(query_hash, ttl_seconds=effective_ttl if effective_ttl > 0 else None)

            if cache and effective_ttl != 0:

                logger.info(f"ℹ️ Found search results in cache for: {query} ({engine})")

                return cache['results']



        # 2. 執行真實搜尋

        logger.info(f"📡 Searching {engine} for: {query}")

        try:

            tool = self._engines[engine]

            if engine == "jina":

                # Jina Search 回傳 List[Dict]

                jina_results = tool.search(query, max_results=max_results)

                results = []

                for r in jina_results:

                    results.append({

                        "title": r.get("title", ""),

                        "href": r.get("url", ""),

                        "body": r.get("content", "")

                    })

            elif engine == "ddg":

                results = tool.duckduckgo_search(query, max_results=max_results)

            elif engine == "baidu":

                results = tool.baidu_search(query, max_results=max_results)

            elif engine == "local":

                # LocalNewsSearch 回傳的是 List[Dict]

                local_results = tool.search(query, top_n=max_results)

                results = []

                for r in local_results:

                    results.append({

                        "title": r.get("title"),

                        "href": r.get("url", "local"),

                        "body": r.get("content", "")

                    })

            else:

                results = "Search not implemented for this engine."

            

            results_str = str(results)

            if engine != "local":

                self.db.save_search_cache(query_hash, query, engine, results_str)

            return results_str

            

        except Exception as e:

            # 搜尋失敗時的降級策略

            if engine == "jina":

                logger.warning(f"⚠️ Jina search failed, falling back to ddg: {query} ({e})")

                try:

                    return self.search(query, engine="ddg", max_results=max_results, ttl=ttl)

                except Exception as e2:

                    logger.error(f"❌ DDG fallback also failed for {query}: {e2}")

            elif engine == "ddg":

                logger.warning(f"⚠️ DDG search failed, falling back to baidu: {query} ({e})")

                try:

                    return self.search(query, engine="baidu", max_results=max_results, ttl=ttl)

                except Exception as e2:

                    logger.error(f"❌ Baidu fallback also failed for {query}: {e2}")



            logger.error(f"❌ Search failed for {query}: {e}")

            return f"Error occurred during search: {str(e)}"



    def search_list(self, query: str, engine: str = None, max_results: int = 5, ttl: Optional[int] = None, enrich: bool = True, market: Optional[str] = None) -> List[Dict]:

        """

        執行搜尋並回傳結構化列表 (List[Dict])。

        Dict 套件含: title, href (or url), body (or snippet)



        Args:

            engine: 搜尋引擎，預設使用配置的預設引擎（Jina 優先）

            enrich: 是否抓取正文內容 (預設 True)

            market: 市場類型，可選 "us"、"tw"。若未指定且 engine 為 None，

                    會根據 query 自動偵測。

        """

        # 使用預設引擎

        if engine is None:

            detected_market = self._detect_market(query) if market is None else market

            engine = self._select_engine(detected_market)

            

        if engine not in self._engines:

            logger.error(f"Unsupported engine {engine}")

            return []

            

        # 不同的 hash 以區分是否 enrichment

        enrich_suffix = ":enriched" if enrich else ""

        query_hash = self._generate_hash(query, engine + enrich_suffix, max_results)

        effective_ttl = ttl if ttl is not None else DEFAULT_SEARCH_TTL

        

        # 1. 嘗試從快取讀取

        cache = self.db.get_search_cache(query_hash, ttl_seconds=effective_ttl if effective_ttl > 0 else None)

        if cache and effective_ttl != 0:

            try:

                cached_data = json.loads(cache['results'])

                if isinstance(cached_data, list):

                    logger.info(f"ℹ️ Found structured search cache for: {query}")

                    return cached_data

            except:

                pass

        

        # 1.5 Smart Cache (Delegated to Agent)

        # The Agent should call list_similar_searches and judge relevance using PROMPTS.md



        

        # 2. 執行搜尋

        logger.info(f"📡 Searching {engine} (structured) for: {query}")

        try:

            tool = self._engines[engine]

            results = []

            if engine == "jina":

                # Jina Search 直接回傳結構化資料

                jina_results = tool.search(query, max_results=max_results)

                for r in jina_results:

                    results.append({

                        "title": r.get("title", ""),

                        "url": r.get("url", ""),

                        "href": r.get("url", ""),

                        "body": r.get("content", ""),

                        "content": r.get("content", ""),

                        "source": "Jina Search"

                    })

            elif engine == "ddg":

                results = tool.duckduckgo_search(query, max_results=max_results)

            elif engine == "baidu":

                results = tool.baidu_search(query, max_results=max_results)

            elif engine == "local":

                # LocalNewsSearch 回傳的是 List[Dict]

                local_results = tool.search(query, top_n=max_results)

                results = []

                for r in local_results:

                    results.append({

                        "title": r.get("title"),

                        "url": r.get("url", "local"),

                        "body": r.get("content", "")[:500],

                        "source": f"Local ({r.get('source', 'db')})",

                        "publish_time": r.get("publish_time")

                    })

            

            # 處理字串類別型的 JSON 回傳 (Baidu 常返 JSON 字串)

            if isinstance(results, str) and engine not in ["local", "jina"]:

                try:

                    results = json.loads(results)

                except:

                    pass

            

            # 轉為統一格式

            normalized_results = []

            if isinstance(results, list):

                

                for i, r in enumerate(results, 1):

                    title = r.get('title', '')

                    url = r.get('href') or r.get('url') or r.get('link', '')

                    content = r.get('body') or r.get('snippet') or r.get('abstract', '')

                    

                    if title and url:

                        normalized_results.append({

                            "id": self._generate_hash(url + query, "search_item", i),

                            "rank": i,

                            "title": title,

                            "url": url,

                            "content": content,

                            "original_snippet": content, # 保留摘要

                            "source": f"Search ({engine})",

                            "publish_time": datetime.now().isoformat(), # 暫用當前時間

                            "crawl_time": datetime.now().isoformat(),

                            "meta_data": {"query": query, "engine": engine}

                        })

            

            # Fallback if still string and failed to parse

            elif isinstance(results, str) and results:

                 normalized_results.append({"title": query, "url": "", "content": results, "source": engine})



            # 3. 抓取正文 & 計算情緒 (Enrichment)

            # 注意：如果使用 Jina Search，內容已經是 LLM 友好格式，可選擇跳過 enrichment

            skip_content_enrichment = (engine == "jina")

            if enrich and normalized_results:
                logger.info(f"🕸️ Enriching {len(normalized_results)} search results...")
                extractor = ContentExtractor()

                for item in normalized_results:
                    if item.get("url"):
                        try:
                            if skip_content_enrichment and item.get("content") and len(item.get("content", "")) > 100:
                                full_content = item["content"]
                            else:
                                full_content = extractor.extract_with_jina(item["url"], timeout=60)

                            if full_content and len(full_content) > 100:
                                item["content"] = full_content
                                logger.info(f"  Enriched: {item['title'][:20]}...")
                        except Exception as e:
                            logger.warning(f"Failed to enrich {item['url']}: {e}.")

            # 快取結果 list

            if normalized_results:

                # Pass list directly, DB manager will handle JSON dump for main cache and populate search_details

                # Only cache if NOT from local news reuse (though this logic path is for fresh search)

                self.db.save_search_cache(query_hash, query, engine, normalized_results)

            

            return normalized_results

            

        except Exception as e:

            # 搜尋失敗時的降級策略

            if engine == "jina":

                logger.warning(f"⚠️ Jina search_list failed, falling back to ddg: {query} ({e})")

                try:

                    return self.search_list(query, engine="ddg", max_results=max_results, ttl=ttl, enrich=enrich)

                except Exception as e2:

                    logger.error(f"❌ DDG fallback (search_list) also failed for {query}: {e2}")

            elif engine == "ddg":

                logger.warning(f"⚠️ DDG search_list failed, falling back to baidu: {query} ({e})")

                try:

                    return self.search_list(query, engine="baidu", max_results=max_results, ttl=ttl, enrich=enrich)

                except Exception as e2:

                    logger.error(f"❌ Baidu fallback (search_list) also failed for {query}: {e2}")



            logger.error(f"❌ Structured search failed for {query}: {e}")

            return []



    def list_similar_queries(self, query: str, limit: int = 5) -> List[Dict]:

        """

        尋找與當前查詢類別似的已快取查詢。

        Agent 可用此方法取得候選快取，並使用 PROMPTS.md 進行評估以決定是否重用。

        """

        return self.db.find_similar_queries(query, limit=limit)





    def aggregate_search(self, query: str, engines: Optional[List[str]] = None, max_results: int = 5) -> str:

        """

        使用多個搜尋引擎同時搜尋並聚合結果，獲得更全面的資訊覆蓋。

        

        Args:

            query: 搜尋關鍵詞。

            engines: 要使用的搜尋引擎列表。可選值: ["ddg", "baidu"]。

                     預設同時使用 ddg 和 baidu。

            max_results: 每個引擎期望回傳的結果數量。

        

        Returns:

            聚合後的搜尋結果，按引擎分組顯示。

        """

        engines = engines or ["ddg", "baidu"]

        aggregated_results = []

        for engine in engines:

            res = self.search(query, engine=engine, max_results=max_results)

            aggregated_results.append(f"--- Results from {engine.upper()} ---\n{res}")

        

        return "\n\n".join(aggregated_results)

    def _fetch_price(self, ticker: str, market: str) -> Optional[Dict]:
        """使用 yfinance 取得即時股價。

        Args:
            ticker: 股票代碼（如 'AAPL' 或 '2330'）
            market: 市場類型 ('us' 或 'tw')

        Returns:
            dict with price, currency, change, change_pct 或 None
        """
        if not ticker or not ticker.strip():
            return None

        ticker = ticker.strip().upper()

        # 台股加上 .TW 後綴
        if market == "tw" and not ticker.endswith(".TW"):
            ticker = f"{ticker}.TW"

        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or "regularMarketPrice" not in info:
                logger.warning(f"⚠️ No price data for {ticker}")
                return None

            currency = info.get("currency", "USD" if market == "us" else "TWD")
            return {
                "price": info.get("regularMarketPrice"),
                "currency": currency,
                "change": info.get("regularMarketChange"),
                "change_pct": info.get("regularMarketChangePercent"),
                "source": "yfinance",
            }

        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch price for {ticker}: {e}")
            return None

    def _extract_tickers(self, query: str) -> List[str]:
        """從查詢字串中提取可能的股票代碼。

        Args:
            query: 搜尋查詢字串

        Returns:
            提取到的 ticker 列表（去重）
        """
        tickers = []
        if not query:
            return tickers

        # 提取美股 ticker（2-5 大寫字母）
        for match in US_TICKER_RE.finditer(query):
            ticker = match.group()
            # 排除常見非 ticker 的英文縮寫
            if ticker not in ("API", "CEO", "CFO", "GDP", "IPO", "VPN", "ETF", "AI", "IT"):
                tickers.append(ticker)

        # 提取台股代號（4 碼數字）
        for match in TW_TICKER_RE.finditer(query):
            tickers.append(match.group())

        # 去重保留順序
        seen = set()
        unique = []
        for t in tickers:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique


