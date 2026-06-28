---
name: alphaear-news
description: 從 RSS 來源（中央社、Bloomberg、Reuters、NHK）抓取財經新聞，以及 Polymarket 預測市場資料。當使用者需要台灣/美國/日本市場的即時財經新聞，或預測市場資料時使用。
---

# AlphaEar News Skill

## 功能概述

從精選 RSS 來源抓取即時財經新聞，以及 Polymarket 預測市場資料。

## 使用方式

### 1. 抓取新聞

使用 `scripts/news_tools.py` 中的 `NewsFetcher`。

- **單一來源**：`fetch_hot_news(source_id, count=15)`
  - 有效 source_id：`cna_finance`、`cna_tech`、`nhk_economy`、`bloomberg`、`investing_reuters`
  - 完整列表見 [sources.md](references/sources.md)
- **全部來源**：`fetch_all_sources(sources=None, count=15)`
- **彙整報告**：`get_unified_trends(sources=None, count=10)`
  - 將多個來源的新聞聚合為格式化 Markdown 報告

### 2. 抓取預測市場

使用 `scripts/news_tools.py` 中的 `PolymarketTools`。

- **市場列表**：`get_active_markets(limit=20)`
- **市場摘要**：`get_market_summary(limit=10)`

## 相依套件

- `requests`、`feedparser`、`loguru`
- `scripts/database_manager.py`（本機 SQLite 資料庫）
