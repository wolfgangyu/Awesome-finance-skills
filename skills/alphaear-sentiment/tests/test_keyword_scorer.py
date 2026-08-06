"""Simplified test script for alphaear-sentiment keyword scoring.

Usage:
    python test_keyword_scorer.py
"""

import sys
import os
from pathlib import Path
import json
import sqlite3

# Add skill root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.keyword_scorer import KeywordScorer


def test_keyword_scorer():
    """Test KeywordScorer directly."""
    print("🧪 Testing KeywordScorer...")
    scorer = KeywordScorer()

    # Test zh-TW
    zh_test = "台積電宣布 2nm 量產時程提前，外資上調目標價至 2000 元。"
    result = scorer.score_news(zh_test)
    print(f"zh-TW test: score={result['score']}, language={result['language']}")
    print(f"  Matched: {result['matched_keywords']}")

    # Test ja
    ja_test = "ソニーグループが過去最高益を発表、AI事業が好調。"
    result = scorer.score_news(ja_test)
    print(f"ja test: score={result['score']}, language={result['language']}")
    print(f"  Matched: {result['matched_keywords']}")

    # Test en
    en_test = "NVIDIA stock surges after record high earnings report."
    result = scorer.score_news(en_test)
    print(f"en test: score={result['score']}, language={result['language']}")
    print(f"  Matched: {result['matched_keywords']}")

    # Test neutral
    neutral_test = "台積電公布 7 月營收，年增 5.2% 符合市場預期。"
    result = scorer.score_news(neutral_test)
    print(f"neutral test: score={result['score']}, language={result['language']}")
    print(f"  Matched: {result['matched_keywords']}")


def test_database_integration():
    """Test database integration with manual SQLite connection."""
    print("\n🧪 Testing database integration...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create test table
    cursor.execute("""
        CREATE TABLE daily_news (
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

    # Insert test data
    test_news = [
        {
            "id": "test1",
            "source": "cna_finance",
            "title": "台積電宣布 2nm 量產時程提前，外資上調目標價至 2000 元",
            "content": "台積電今日宣布 2nm 製程量產時程將提前至 2025 年上半年，較原計畫提早半年。外資機構紛紛上調目標價，其中高盛將目標價上調至 2000 元，維持買進評級。",
            "meta_data": json.dumps({"language": "zh-TW"})
        },
        {
            "id": "test2",
            "source": "nhk_economy",
            "title": "ソニーグループが過去最高益を発表、AI事業が好調",
            "content": "ソニーグループは2026年3月期決算を発表し、過去最高の営業利益を達成した。特にAI関連事業が好調で、売上高は前年比15%増加した。",
            "meta_data": json.dumps({"language": "ja"})
        },
        {
            "id": "test3",
            "source": "bloomberg",
            "title": "NVIDIA stock surges after record high earnings report",
            "content": "NVIDIA shares jumped 12% in after-hours trading following a better-than-expected earnings report. The company reported record revenue of $26 billion, driven by strong demand for AI chips.",
            "meta_data": json.dumps({"language": "en"})
        },
        {
            "id": "test4",
            "source": "cna_finance",
            "title": "台積電公布 7 月營收，年增 5.2% 符合市場預期",
            "content": "台積電 (2330) 今日公布 7 月合併營收為新台幣 2,432.1 億元，年增 5.2%，符合市場預期。累計前七月營收為新台幣 1.63 兆元，年增 28.7%。",
            "meta_data": json.dumps({"language": "zh-TW"})
        }
    ]

    for news in test_news:
        cursor.execute("""
            INSERT INTO daily_news
            (id, source, title, content, meta_data, sentiment_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            news["id"],
            news["source"],
            news["title"],
            news["content"],
            news["meta_data"],
            None  # No sentiment_score initially
        ))

    conn.commit()

    # Test scoring logic
    scorer = KeywordScorer()
    success_count = 0

    for news in test_news:
        try:
            news_id = news["id"]
            title = news["title"]
            content = news["content"]
            meta_data = json.loads(news["meta_data"])
            language = meta_data.get("language")

            # Score the news
            result = scorer.score_news(title, content, language)

            # Update database
            meta_data["sentiment_keywords"] = result["matched_keywords"]
            cursor.execute("""
                UPDATE daily_news
                SET sentiment_score = ?, meta_data = ?
                WHERE id = ?
            """, (result["score"], json.dumps(meta_data), news_id))

            success_count += 1
            print(f"Scored news {news_id}: {result['score']}")
        except Exception as e:
            print(f"Error scoring news {news['id']}: {e}")

    conn.commit()

    # Check results
    cursor.execute("SELECT id, sentiment_score, meta_data FROM daily_news ORDER BY id")
    results = cursor.fetchall()

    for row in results:
        news_id, score, meta_data = row
        meta_dict = json.loads(meta_data) if meta_data else {}
        keywords = meta_dict.get("sentiment_keywords", [])
        print(f"News {news_id}: score={score}, keywords={len(keywords)} matches")

    conn.close()
    print(f"Successfully scored {success_count}/{len(test_news)} news items")


if __name__ == "__main__":
    test_keyword_scorer()
    test_database_integration()
    print("\n✅ All tests completed!")