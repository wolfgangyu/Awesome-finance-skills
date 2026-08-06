"""
Test script for sentiment tools functionality
"""
import sys
import os
import json
import sqlite3
from datetime import datetime

# Add the correct path to Python path
sys.path.insert(0, os.path.abspath('.'))

# Mock DatabaseManager
class MockDatabaseManager:
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
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
                meta_data TEXT
            )
        """)
        self.conn.commit()

    def get_daily_news(self, source=None, limit=50):
        cursor = self.conn.cursor()
        query = "SELECT * FROM daily_news"
        params = []
        if source:
            query += " WHERE source = ?"
            params.append(source)
        query += " ORDER BY crawl_time DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "source": row[1],
                "rank": row[2],
                "title": row[3],
                "url": row[4],
                "content": row[5],
                "publish_time": row[6],
                "crawl_time": row[7],
                "sentiment_score": row[8],
                "meta_data": json.loads(row[9]) if row[9] else {}
            })
        return results

    def close(self):
        self.conn.close()

# Import the sentiment tools
from skills.alphaear_sentiment.scripts.sentiment_tools import SentimentTools

def test_sentiment_tools():
    # Create mock database
    db = MockDatabaseManager()

    # Insert test data
    cursor = db.conn.cursor()
    test_news = [
        ("1", "cna_finance", 1, "台積電宣布 2nm 量產時程提前，外資上調目標價至 2000 元",
         "https://example.com/1", "台積電宣布 2nm 量產時程提前...",
         "2026-08-06", datetime.now().isoformat(), None, json.dumps({"language": "zh-TW"})),
        ("2", "nhk_economy", 1, "TSMCが2nmの量産スケジュールを前倒し、外資が目標株価を2000元に引き上げ",
         "https://example.com/2", "TSMCが2nmの量産スケジュールを前倒し...",
         "2026-08-06", datetime.now().isoformat(), None, json.dumps({"language": "ja"})),
        ("3", "bloomberg", 1, "TSMC accelerates 2nm production schedule",
         "https://example.com/3", "TSMC accelerates 2nm production...",
         "2026-08-06", datetime.now().isoformat(), None, json.dumps({"language": "en"})),
        ("4", "cna_finance", 2, "台積電南科廠區火災，產線停工估計影響 3% 產能",
         "https://example.com/4", "台積電南科廠區火災...",
         "2026-08-06", datetime.now().isoformat(), None, json.dumps({"language": "zh-TW"})),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO daily_news
        (id, source, rank, title, url, content, publish_time, crawl_time, sentiment_score, meta_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, test_news)
    db.conn.commit()

    # Test sentiment tools
    tools = SentimentTools(db)

    # Test batch update
    updated_count = tools.batch_update_news_sentiment()
    print(f"Batch updated {updated_count} news items")

    # Check results
    news_items = db.get_daily_news()
    for item in news_items:
        print(f"News {item['id']}: score={item.get('sentiment_score', 'None')}, title={item['title']}")

    db.close()

if __name__ == "__main__":
    test_sentiment_tools()