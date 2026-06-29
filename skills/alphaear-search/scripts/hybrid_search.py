import numpy as np

import os

from typing import List, Dict, Any, Optional, Union

from rank_bm25 import BM25Okapi

from loguru import logger

from sentence_transformers import SentenceTransformer

from sklearn.metrics.pairwise import cosine_similarity



class HybridSearcher:

    """

    統一混合檢索引擎 (Hybrid RAG)

    實現 BM25 (文字) + 向量 (語義) 的融合搜尋 (RRF)

    """

    

    def __init__(self, data: List[Dict[str, Any]], text_fields: List[str] = ["title", "content"], model_name: str = None):

        """

        初始化搜尋器

        

        Args:

            data: 資料列表，每個元素為 Dict

            text_fields: 用於建立索引的文字欄位

            model_name: 向量模型名稱，預設使用 paraphrase-multilingual-MiniLM-L12-v2

        """

        self.data = data

        self.text_fields = text_fields

        self._corpus = []

        self._bm25 = None

        self._vector_model = None

        self._embeddings = None

        self._fitted = False

        self._vector_fitted = False

        

        # 預設模型

        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

        

        if data:

            self._prepare_corpus()

            self._fit_bm25()

            # 延遲載入向量模型，僅在需要時或初始化時顯式呼叫

            # self._fit_vector() 



    def _prepare_corpus(self):

        """準備語料庫用於分詞"""

        import jieba  # 使用 jieba 進行中文分詞

        

        self._corpus = []

        self._full_texts = []

        for item in self.data:

            text = " ".join([str(item.get(field, "")) for field in self.text_fields])

            self._full_texts.append(text)

            # 中文分詞最佳化

            tokens = list(jieba.cut(text))

            self._corpus.append(tokens)



    def _fit_bm25(self):

        """訓練 BM25 模型"""

        if self._corpus:

            self._bm25 = BM25Okapi(self._corpus)

            self._fitted = True

            logger.info(f"✅ BM25 index fitted with {len(self.data)} documents")



    def _fit_vector(self):

        """訓練向量模型並生成 Embeddings"""

        if not self.data:

            return

            

        try:

            logger.info(f"📡 Loading embedding model: {self.model_name}...")

            self._vector_model = SentenceTransformer(self.model_name)

            logger.info(f"🧠 Encoding {len(self._full_texts)} documents...")

            self._embeddings = self._vector_model.encode(self._full_texts, show_progress_bar=False)

            self._vector_fitted = True

            logger.info("✅ Vector index fitted successfully")

        except Exception as e:

            logger.error(f"❌ Failed to fit vector index: {e}")

            self._vector_fitted = False



    def _compute_rrf(self, rank_lists: List[List[int]], k: int = 60) -> List[tuple]:

        """

        計算 Reciprocal Rank Fusion (RRF)

        

        Args:

            rank_lists: 多個排序後的索引列表

            k: RRF 常數，預設 60

        """

        scores = {}

        for rank_list in rank_lists:

            for rank, idx in enumerate(rank_list):

                if idx not in scores:

                    scores[idx] = 0

                scores[idx] += 1.0 / (k + rank + 1)

        

        # 按分數排序

        sorted_indices = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_indices



    def search(self, query: str, top_n: int = 5, use_vector: bool = False) -> List[Dict[str, Any]]:

        """

        執行混合搜尋

        

        Args:

            query: 搜尋關鍵詞

            top_n: 回傳結果數量

            use_vector: 是否啟用向量搜尋

        """

        if not self._fitted or not query:

            return []

        

        import jieba

        query_tokens = list(jieba.cut(query))

        

        # 1. BM25 搜尋結果

        bm25_scores = self._bm25.get_scores(query_tokens)

        bm25_rank = np.argsort(bm25_scores)[::-1].tolist()

        

        rank_lists = [bm25_rank]

        

        # 2. 向量搜尋邏輯

        if use_vector:

            if not self._vector_fitted:

                self._fit_vector()

            

            if self._vector_fitted:

                query_embedding = self._vector_model.encode([query], show_progress_bar=False)

                similarities = cosine_similarity(query_embedding, self._embeddings)[0]

                vector_rank = np.argsort(similarities)[::-1].tolist()

                rank_lists.append(vector_rank)

            else:

                logger.warning("Vector search requested but model not fitted, falling back to BM25")

        

        # 3. 融合排序 (RRF)

        if len(rank_lists) > 1:

            rrf_results = self._compute_rrf(rank_lists)

            # RRF 回傳 (idx, score) 列表

            final_rank = [idx for idx, score in rrf_results]

        else:

            final_rank = bm25_rank

        

        # 回傳前 top_n 條結果

        results = [self.data[idx].copy() for idx in final_rank[:top_n]]

        

        # 為每個結果注入相關性評分

        for i, res in enumerate(results):

            try:

                original_idx = final_rank[i]

                res["_search_score"] = bm25_scores[original_idx]

                if use_vector and self._vector_fitted:

                    res["_vector_score"] = float(similarities[original_idx])

            except:

                res["_search_score"] = 0

            

        return results



class InMemoryRAG(HybridSearcher):

    """專門用於 ReportAgent 跨章節檢索的記憶體態 RAG"""

    

    def search(self, query: str, top_n: int = 3, use_vector: bool = True) -> List[Dict[str, Any]]:

        """預設開啟向量搜尋的記憶體檢索"""

        return super().search(query, top_n=top_n, use_vector=use_vector)



    def update_data(self, new_data: List[Dict[str, Any]]):

        """動態更新資料並重新訓練索引"""

        self.data = new_data

        self._prepare_corpus()

        self._fit_bm25()

        # 如果之前已經載入過向量模型，則更新向量索引

        if self._vector_model:

            self._fit_vector()

        logger.info(f"🔄 InMemoryRAG updated with {len(new_data)} items")



class LocalNewsSearch(HybridSearcher):

    """持久態 RAG：檢索資料庫中的歷史新聞"""

    

    def __init__(self, db_manager):

        """

        Args:

            db_manager: DatabaseManager 例項

        """

        self.db = db_manager

        # 初始時不載入資料，需呼叫 load_history

        super().__init__([], ["title", "content"])

    

    def load_history(self, days: int = 30, limit: int = 1000):

        """從資料庫載入最近 N 天的新聞構建索引"""

        try:

            # 假設 db_manager 有 execute_query

            query = f"SELECT title, content, publish_time, source FROM daily_news ORDER BY publish_time DESC LIMIT ?"

            results = self.db.execute_query(query, (limit,))

            

            data = []

            for row in results:

                # 轉換 Row 為 Dict

                if hasattr(row, 'keys'):

                    item = dict(row)

                else:

                    item = {

                        "title": row[0], 

                        "content": row[1], 

                        "publish_time": row[2],

                        "source": row[3]

                    }

                data.append(item)

            

            self.data = data

            self._prepare_corpus()

            self._fit_bm25()

            # 預設不立即訓練向量，等到第一次搜尋時按需訓練

            logger.info(f"📚 LocalNewsSearch loaded {len(data)} items from history")

        except Exception as e:

            logger.error(f"Failed to load history for search: {e}")



    def search(self, query: str, top_n: int = 5, use_vector: bool = True) -> List[Dict[str, Any]]:

        """執行本機歷史搜尋，預設開啟向量搜尋"""

        if not self.data:

            self.load_history()

        return super().search(query, top_n=top_n, use_vector=use_vector)

