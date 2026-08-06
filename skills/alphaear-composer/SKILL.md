# AlphaEar Composer Skill

Automatically assemble raw data from news, search, and stock skills into a unified `latest.json` investment signal report. Now supports **automated sentiment scoring** from alphaear-sentiment.

## Overview

AlphaEar Composer orchestrates the data pipeline from raw inputs to structured signals. It now integrates **automated sentiment scoring** for Chinese (zh-TW), Japanese (ja), and English news.

## Data Flow

```
alphaear-news      →  aggregated financial news (CNA, Bloomberg, NHK, etc.)
alphaear-stock     →  stock prices (TWSE, TPEx, yfinance)
alphaear-search    →  web search results
alphaear-sentiment →  automated sentiment scores (zh-TW, ja, en)
│
▼
alphaear-composer  →  latest.json (unified report)
```

## Key Features

### 1. Automated Sentiment Integration

Composer now automatically incorporates sentiment scores from `alphaear-sentiment`:

- **Chinese (zh-TW)**: Central News Agency (CNA) financial news
- **Japanese (ja)**: NHK economic news
- **English (en)**: Bloomberg, Reuters news

The sentiment scores are used in ISQ scoring to calculate:
- `sentiment_score`: -1.0 (bearish) to +1.0 (bullish)
- `confidence`: 0.0 to 1.0 (based on news volume and consistency)
- `intensity`: 1 to 5 (impact magnitude)

### 2. Heuristic ISQ Scoring

The `heuristic_score()` function calculates ISQ metrics from:

```python
{
    "sentiment_score": average_sentiment,  # From alphaear-sentiment
    "confidence": min(1.0, 0.3 + 0.1 * log(news_count)),
    "intensity": 1-5,  # Based on news volume and price changes
    "expectation_gap": min(1.0, max_price_change / 20.0),
    "timeliness": 0.7  # Higher for recent news
}
```

### 3. Market Filtering

Support for filtering by market:
- `tw`: Taiwan market only
- `us`: US market only
- `both`: Both markets (default)

## Usage

### Run Full Pipeline

```bash
# Run with default settings (1 day, both markets)
python3 skills/alphaear-composer/scripts/composer.py

# Specify days and market
python3 skills/alphaear-composer/scripts/composer.py --days 3 --market tw
```

### Read Existing latest.json

```bash
# Format and display latest.json
python3 skills/alphaear-composer/scripts/composer.py --read
```

## Output Format

The generated `data/latest.json` is compatible with DeepEar Lite:

```json
{
  "generated_at": "2026-08-06T12:00:00",
  "signals": [
    {
      "signal_id": "TSMC",
      "title": "台積電宣布 2nm 量產提前",
      "summary": "台積電宣布 2nm 量產時程提前...",
      "sentiment_score": 0.5,
      "confidence": 0.85,
      "intensity": 4,
      "sources": [{"title": "...", "url": "..."}]
    }
  ]
}
```

## Dependencies

- `alphaear-news`: For news data
- `alphaear-stock`: For stock prices
- `alphaear-sentiment`: For automated sentiment scoring
- `sqlite3`: For database access
- `loguru`: For logging