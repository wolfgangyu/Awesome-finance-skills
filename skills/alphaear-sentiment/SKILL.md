---
name: alphaear-sentiment
description: Analyze sentiment of financial news and text. Use when the user asks to evaluate market sentiment, determine if news is positive or negative, or needs a sentiment score for financial text.
---

# AlphaEar Sentiment Skill

## Overview

This skill guides the Agent to perform sentiment analysis on financial texts. Instead of relying on local models (BERT/FinBERT), it delegates analysis directly to the Agent's reasoning capabilities.

## How to Perform Sentiment Analysis

When analyzing financial news or text, follow these steps:

### 1. Evaluate Sentiment

Read the text and determine:
- **Positive (+0.1 to +1.0)**: Bullish signals, earnings growth, policy tailwinds, product launches, analyst upgrades
- **Negative (-1.0 to -0.1)**: Bearish signals, losses, sanctions, price drops, analyst downgrades, regulatory risks
- **Neutral (-0.1 to +0.1)**: Factual reporting, consolidation, ambiguous impact

### 2. Return Structured Result

Always return a JSON object with these fields:

```json
{"score": <float: -1.0 ~ 1.0>, "label": "<positive/negative/neutral>", "reason": "<brief explanation in Traditional Chinese>"}
```

### 3. Examples

**Positive example:**
> Text: "Apple announces M7 chip roadmap shift toward AI, BofA maintains bullish outlook."
> Result: `{"score": 0.5, "label": "positive", "reason": "晶片路線圖轉向AI為長期利多，機構維持看好"}`

**Negative example:**
> Text: "KGI downgrades Apple to Hold from Outperform; Apple raises prices for the first time since COVID."
> Result: `{"score": -0.6, "label": "negative", "reason": "評級下調加上破天荒漲價，短期利空明顯"}`

**Neutral example:**
> Text: "Apple stock closed at $283.60, down 3% from yesterday's intraday high."
> Result: `{"score": 0.0, "label": "neutral", "reason": "客觀行情報導，無明確多空訊號"}`

## Saving Results to Database

If you need to save your analysis to the database, use:

```python
from scripts.database_manager import DatabaseManager
from scripts.sentiment_tools import SentimentTools

db = DatabaseManager("data/signal_flux.db")
tools = SentimentTools(db)
tools.update_single_news_sentiment(news_id, score, reason)
```

## Dependencies

- `sqlite3` (built-in)
- `loguru`

No external ML libraries required.
