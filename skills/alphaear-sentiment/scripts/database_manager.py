import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import pandas as pd
from loguru import logger

class DatabaseManager:
    """
    AlphaEar 資料庫管理器 - 負責儲存新聞資料、搜尋快取
    使用 SQLite 進行持久化儲存
    """

    def __init__(self, db_path: str = "data/signal_flux.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        logger.info(f"💾 Database initialized at {self.db_path}")

    def _init_db(self):
        """初始化表結構"""
        cursor = self.conn.cursor()

        # 1. 每日熱門新聞表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_news (
                id TEXT PRIMARY KEY,
                source TEXT,
                rank INTEGER,
                title TEXT,
                url TEXT,
                content TEXT,
                publish_time TEXT,
                crawl_time TEXT,
                sentiment_score REAL,
                analysis TEXT,
                meta_data TEXT
            )
        """)

        # 嘗試添加 analysis 列（如果表已存在但沒有該列）
        try:
            cursor.execute("ALTER TABLE daily_news ADD COLUMN analysis TEXT")
        except:
            pass  # 列已存在

        # 2. 搜尋快取表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                engine TEXT,
                results TEXT,
                timestamp TEXT
            )
        """)

        # 2.5 搜尋詳情表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_detail (
                id TEXT,
                query_hash TEXT,
                rank INTEGER,
                title TEXT,
                url TEXT,
                content TEXT,
                publish_time TEXT,
                crawl_time TEXT,
                sentiment_score REAL,
                source TEXT,
                meta_data TEXT,
                PRIMARY KEY (query_hash, id)
            )
        """)

        # 3. 創建索引以優化查詢效能
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_crawl_time ON daily_news(crawl_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_source ON daily_news(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_cache_timestamp ON search_cache(timestamp)")

        self.conn.commit()

    # --- 新聞資料操作 ---

    def save_daily_news(self, news_list: List[Dict]) -> int:
        """保存熱門新聞，套件含發布時間與抓取時間"""
        cursor = self.conn.cursor()
        count = 0
        crawl_time = datetime.now().isoformat()

        for news in news_list:
            try:
                # 相容不同來源的 ID 生成邏輯
                news_id = news.get('id') or f"{news.get('source')}_{news.get('rank')}_{crawl_time[:10]}"
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_news
                    (id, source, rank, title, url, content, publish_time, crawl_time, sentiment_score, meta_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    news_id,
                    news.get('source'),
                    news.get('rank'),
                    news.get('title'),
                    news.get('url'),
                    news.get('content', ''),
                    news.get('publish_time'),
                    crawl_time,
                    news.get('sentiment_score'),
                    json.dumps(news.get('meta_data', {}))
                ))
                count += 1
            except sqlite3.Error as e:
                logger.error(f"Database error saving news item {news.get('title')}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error saving news item {news.get('title')}: {e}")

        self.conn.commit()
        return count

    def get_daily_news(self, source: Optional[str] = None, limit: int = 100, days: int = 1) -> List[Dict]:
        """取得最近 N 天的熱門新聞"""
        cursor = self.conn.cursor()
        # 使用 crawl_time 過濾，保證結果的新鮮度
        time_threshold = (datetime.now().timestamp() - days * 86400)
        time_threshold_str = datetime.fromtimestamp(time_threshold).isoformat()

        query = "SELECT * FROM daily_news WHERE crawl_time >= ?"
        params = [time_threshold_str]

        if source:
            query += " AND source = ?"
            params.append(source)

        query += " ORDER BY crawl_time DESC, rank LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def lookup_reference_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Best-effort lookup of a source item by URL."""
        url = (url or "").strip()
        if not url:
            return None

        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                SELECT title, source, publish_time, crawl_time, url
                FROM daily_news
                WHERE url = ?
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (url,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception:
            pass

        try:
            cursor.execute("""
                SELECT title, source, publish_time, crawl_time, url
                FROM search_detail
                WHERE url = ?
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (url,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception:
            pass

        return None

    def delete_news(self, news_id: str) -> bool:
        """刪除特定新聞"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM daily_news WHERE id = ?", (news_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_news_content(self, news_id: str, content: str = None, analysis: str = None) -> bool:
        """更新新聞的內容或分析結果"""
        cursor = self.conn.cursor()
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if analysis is not None:
            updates.append("analysis = ?")
            params.append(analysis)

        if not updates:
            return False

        params.append(news_id)
        query = f"UPDATE daily_news SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.rowcount > 0

    # --- 搜尋快取輔助 ---

    def get_search_cache(self, query_hash: str, ttl_seconds: Optional[int] = None) -> Optional[Dict]:
        """取得搜尋快取 (優先查 search_detail)"""
        cursor = self.conn.cursor()

        # 1. 嘗試從 search_detail 取得展開的結構化資料
        cursor.execute("""
            SELECT * FROM search_detail
            WHERE query_hash = ?
            ORDER BY rank
        """, (query_hash,))
        details = [dict(row) for row in cursor.fetchall()]

        if details:
            # 檢查 TTL
            first_time = datetime.fromisoformat(details[0]['crawl_time'])
            if ttl_seconds and (datetime.now() - first_time).total_seconds() > ttl_seconds:
                logger.info(f"⌛ Detailed cache expired for hash {query_hash}")
                return None

            logger.info(f"✅ Hit detailed search cache for {query_hash} ({len(details)} items)")
            return {"results": json.dumps(details), "timestamp": details[0]['crawl_time']}

        # 2. Fallback to old table
        cursor.execute("SELECT * FROM search_cache WHERE query_hash = ?", (query_hash,))
        row = cursor.fetchone()

        if not row:
            return None

        row_dict = dict(row)
        if ttl_seconds:
            cache_time = datetime.fromisoformat(row_dict['timestamp'])
            if (datetime.now() - cache_time).total_seconds() > ttl_seconds:
                logger.info(f"⌛ Cache expired for hash {query_hash}")
                return None

        return row_dict

    def save_search_cache(self, query_hash: str, query: str, engine: str, results: Union[str, List[Dict]]):
        """保存搜尋結果 (同時保存到 search_cache 和 search_detail)"""
        cursor = self.conn.cursor()
        current_time = datetime.now().isoformat()

        results_str = results if isinstance(results, str) else json.dumps(results)

        # 1. Save summary to search_cache
        cursor.execute("""
            INSERT OR REPLACE INTO search_cache (query_hash, query, engine, results, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (query_hash, query, engine, results_str, current_time))

        # 2. Save details to search_detail if results is a list
        if isinstance(results, list):
            for item in results:
                try:
                    item_id = item.get('id') or f"{hash(item.get('url', ''))}"
                    cursor.execute("""
                        INSERT OR REPLACE INTO search_detail
                        (id, query_hash, rank, title, url, content, publish_time, crawl_time, sentiment_score, source, meta_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(item_id),
                        query_hash,
                        item.get('rank', 0),
                        item.get('title'),
                        item.get('url'),
                        item.get('content', ''),
                        item.get('publish_time'),
                        item.get('crawl_time') or current_time,
                        item.get('sentiment_score'),
                        item.get('source'),
                        json.dumps(item.get('meta_data', {}))
                    ))
                except sqlite3.Error as e:
                    logger.error(f"Database error saving search detail {item.get('title')}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error saving search detail {item.get('title')}: {e}")

        self.conn.commit()

    def find_similar_queries(self, query: str, limit: int = 5) -> List[Dict]:
        """模糊搜尋相似的已快取查詢"""
        cursor = self.conn.cursor()

        q_wild = f"%{query}%"
        cursor.execute("""
            SELECT query, query_hash, timestamp, results
            FROM search_cache
            WHERE query LIKE ? OR ? LIKE ('%' || query || '%')
            ORDER BY timestamp DESC
            LIMIT ?
        """, (q_wild, query, limit))

        return [dict(row) for row in cursor.fetchall()]

    def search_local_news(self, query: str, limit: int = 5) -> List[Dict]:
        """從本機 daily_news 搜尋相關新聞"""
        cursor = self.conn.cursor()
        q_wild = f"%{query}%"
        cursor.execute("""
            SELECT * FROM daily_news
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY crawl_time DESC
            LIMIT ?
        """, (q_wild, q_wild, limit))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")
