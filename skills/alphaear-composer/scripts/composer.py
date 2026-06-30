"""AlphaEar Composer — 主入口。

串接新聞、搜尋、股價資料，自動產出 latest.json。

Usage:
    # 執行完整 pipeline
    python3 scripts/composer.py

    # 指定天數和市場
    python3 scripts/composer.py --days 3 --market tw

    # 僅讀取已產出的 latest.json 並格式化輸出
    python3 scripts/composer.py --read
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# 確保 scripts/ 在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database_manager import ComposerDatabaseManager
from signal_formation import form_signals_from_news
from isq_scoring import composite_score
from serializer import to_latest_json, write_latest_json, read_latest_json


class ComposerTools:
    """Composer 主工具類 — orchestrates 整個 pipeline。"""

    def __init__(self, db_path: str = None):
        self.db = ComposerDatabaseManager(db_path)

    def compose_latest(self, days: int = 1, market: str = "both") -> dict:
        """執行完整 pipeline：讀取 → 形成訊號 → 序列化 → 寫入 latest.json。

        Args:
            days: 取最近 N 天的新聞
            market: "tw" / "us" / "both"

        Returns:
            latest.json 格式的 dict
        """
        logger.info(f"🎵 Starting composer pipeline (days={days}, market={market})")

        # 1. 讀取原始資料
        news_items = self.db.get_recent_news(days=days)
        logger.info(f"📰 Loaded {len(news_items)} news items")

        if not news_items:
            logger.warning("⚠️  No news items found. Make sure to run alphaear-news first.")
            # 產出一份空的 latest.json
            data = to_latest_json([])
            write_latest_json(data)
            return data

        # 2. 取得股價變動（用於 ISQ 評分）
        price_changes = []
        recent_prices = self.db.get_recent_stock_prices(days=days)
        for ticker, prices in recent_prices.items():
            if len(prices) >= 2:
                closes = [p["close"] for p in prices if p.get("close")]
                if len(closes) >= 2:
                    for i in range(1, len(closes)):
                        change = ((closes[i] - closes[i - 1]) / closes[i - 1] * 100) if closes[i - 1] else 0
                        price_changes.append(change)

        # 3. 從新聞形成 signals
        signals = form_signals_from_news(news_items, price_changes if price_changes else None, market)
        logger.info(f"🎯 Formed {len(signals)} signals")

        if not signals:
            logger.warning("⚠️  No signals formed. Check market filter or news content.")
            data = to_latest_json([])
            write_latest_json(data)
            return data

        # 4. 計算整體市場情緒
        sentiments = [s["sentiment_score"] for s in signals]
        overall_sentiment = "positive" if sum(sentiments) / len(sentiments) > 0.1 else (
            "negative" if sum(sentiments) / len(sentiments) < -0.1 else "mixed"
        )

        # 5. 序列化
        data = to_latest_json(signals)

        # 6. 寫入檔案
        write_latest_json(data)

        # 7. 輸出摘要
        logger.info(f"✅ Composer complete: {len(signals)} signals, overall={overall_sentiment}")
        for sig in signals:
            comp = composite_score({
                "confidence": sig["confidence"],
                "intensity": sig["intensity"],
                "expectation_gap": sig["expectation_gap"],
                "timeliness": sig["timeliness"],
            })
            logger.info(f"   Signal: {sig['title'][:30]} (ID={sig['signal_id']}, ISQ={comp})")

        return data

    def fetch_latest_signals(self, source: str = "local") -> str:
        """讀取 latest.json 並格式化為文字報告。

        與 alphaear-deepear-lite 的 fetch_latest_signals() 介面相容。

        Args:
            source: "local" 讀 data/latest.json, "remote" 不支援（需搭配 deepear-lite）

        Returns:
            格式化後的文字報告
        """
        if source == "local":
            data = read_latest_json()
            if not data:
                return "No local latest.json found. Run compose_latest() first."

            generated_at = data.get("generated_at", "Unknown")
            signals = data.get("signals", [])

            if not signals:
                return "No signals found in latest.json."

            report = [f"### AlphaEar Composer Report (Updated: {generated_at})\n"]

            for i, signal in enumerate(signals, 1):
                title = signal.get("title", "No Title")
                summary = signal.get("summary", "No Summary")
                sentiment = signal.get("sentiment_score", 0)
                confidence = signal.get("confidence", 0)
                intensity = signal.get("intensity", 0)
                reasoning = signal.get("reasoning", "No Reasoning")

                report.append(f"#### {i}. {title}")
                report.append(f"**Sentiment**: {sentiment} | **Confidence**: {confidence} | **Intensity**: {intensity}")
                report.append(f"\n**Summary**: {summary}")
                report.append(f"\n**Reasoning**: {reasoning}")

                sources = signal.get("sources", [])
                if sources:
                    report.append("\n**Sources**:")
                    for src in sources:
                        name = src.get("source_name", src.get("title", "Link"))
                        url = src.get("url", "#")
                        report.append(f"- [{name}]({url})")

                report.append("\n" + "-" * 40 + "\n")

            return "\n".join(report)

        else:
            return "Source 'remote' not supported in composer. Use alphaear-deepear-lite for remote fetching."

    def close(self):
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description="AlphaEar Composer — 自動產出 latest.json")
    parser.add_argument("--days", type=int, default=1, help="取最近 N 天的新聞（預設 1）")
    parser.add_argument("--market", choices=["tw", "us", "both"], default="both", help="市場過濾（預設 both）")
    parser.add_argument("--read", action="store_true", help="僅讀取已產出的 latest.json 並格式化輸出")
    args = parser.parse_args()

    # 設定 loguru
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    composer = ComposerTools()
    try:
        if args.read:
            # 僅讀取並格式化輸出
            result = composer.fetch_latest_signals(source="local")
            print(result)
        else:
            # 執行完整 pipeline
            result = composer.compose_latest(days=args.days, market=args.market)
            print(f"\n✅ latest.json written with {result['count']} signals")
            print(f"   Run again with --read to see formatted output")
    finally:
        composer.close()


if __name__ == "__main__":
    main()
