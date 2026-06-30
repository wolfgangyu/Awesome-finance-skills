"""唯讀資料庫管理器 — 從 signal_flux.db 讀取新聞、搜尋、股價資料。"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from loguru import logger


class ComposerDatabaseManager:
    """輕量級唯讀 DB 管理器，專為 composer skill 設計。"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # 預設路徑：repo 根目錄下的 data/signal_flux.db
            self.db_path = Path(__file__).resolve().parents[3] / "data" / "signal_flux.db"
        else:
            self.db_path = Path(db_path)

        if not self.db_path.exists():
            logger.warning(f"⚠️  DB 檔案不存在: {self.db_path}")
            self.conn = None
            return

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"💾 ComposerDatabaseManager connected to {self.db_path}")

    # ------------------------------------------------------------------ #
    #  新聞                                                              #
    # ------------------------------------------------------------------ #

    def get_recent_news(self, days: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """取得最近 N 天的熱門新聞。"""
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        time_threshold = (datetime.now().timestamp() - days * 86400)
        time_threshold_str = datetime.fromtimestamp(time_threshold).isoformat()

        cursor.execute(
            """
            SELECT id, source, rank, title, url, content, publish_time,
                   sentiment_score, meta_data
            FROM daily_news
            WHERE crawl_time >= ?
            ORDER BY crawl_time DESC, rank
            LIMIT ?
            """,
            (time_threshold_str, limit),
        )

        results = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("meta_data"):
                try:
                    d["meta_data"] = json.loads(d["meta_data"])
                except (json.JSONDecodeError, TypeError):
                    d["meta_data"] = {}
            results.append(d)
        return results

    # ------------------------------------------------------------------ #
    #  搜尋                                                              #
    # ------------------------------------------------------------------ #

    def get_all_search_details(self, limit: int = 100) -> List[Dict[str, Any]]:
        """取得所有搜尋詳情（用於補充 signal reasoning）。"""
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, query_hash, rank, title, url, content,
                   publish_time, crawl_time, sentiment_score, source, meta_data
            FROM search_detail
            ORDER BY crawl_time DESC
            LIMIT ?
            """,
            (limit,),
        )

        results = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("meta_data"):
                try:
                    d["meta_data"] = json.loads(d["meta_data"])
                except (json.JSONDecodeError, TypeError):
                    d["meta_data"] = {}
            results.append(d)
        return results

    # ------------------------------------------------------------------ #
    #  股價                                                              #
    # ------------------------------------------------------------------ #

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """取得股票清單。"""
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stock_list ORDER BY code")
        return [dict(row) for row in cursor.fetchall()]

    def get_stock_prices(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """取得最近 N 天的股價資料。"""
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT date, open, close, high, low, volume
            FROM stock_prices
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (ticker, days),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_stock_prices(self, days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """取得所有股票的近期股價（按 ticker 分組）。"""
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT ticker, date, open, close, high, low, volume
            FROM stock_prices
            ORDER BY ticker, date DESC
            """
        )

        result: Dict[str, List[Dict[str, Any]]] = {}
        for row in cursor.fetchall():
            d = dict(row)
            result.setdefault(d["ticker"], []).append({
                "date": d["date"],
                "open": d["open"],
                "close": d["close"],
                "high": d["high"],
                "low": d["low"],
                "volume": d["volume"],
            })
            # 只取每支前 N 筆
            if len(result[d["ticker"]]) > days:
                result[d["ticker"]] = result[d["ticker"]][:days]

        return result

    # ------------------------------------------------------------------ #
    #  工具                                                              #
    # ------------------------------------------------------------------ #

    def ticker_exists(self, ticker: str) -> bool:
        """檢查 ticker 是否在 stock_list 中。"""
        if not self.conn:
            return False
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM stock_list WHERE code = ? LIMIT 1", (ticker,))
        return cursor.fetchone() is not None

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("ComposerDatabaseManager connection closed.")
