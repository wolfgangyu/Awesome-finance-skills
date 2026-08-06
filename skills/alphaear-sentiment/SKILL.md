---
name: alphaear-sentiment
description: Analyze sentiment of financial news and text. Use when the user asks to evaluate market sentiment, determine if news is positive or negative, or needs a sentiment score for financial text. Now supports automated keyword-based scoring for Chinese (zh-TW), Japanese (ja), and English news.
---

# AlphaEar Sentiment Skill

## Overview

This skill guides the Agent to perform sentiment analysis on financial texts. It supports both **Agent-driven analysis** and **automated keyword-based scoring** for:
- **Traditional Chinese (zh-TW)** — CNA, TechNews, etc.
- **Japanese (ja)** — NHK, Nikkei, etc.
- **English (en)** — Bloomberg, Reuters, etc.

## How to Perform Sentiment Analysis

### 1. Automated Keyword Scoring (New!)

The skill now includes **comprehensive keyword dictionaries** for automated sentiment scoring:

```python
from scripts.database_manager import DatabaseManager
from scripts.sentiment_tools import SentimentTools

db = DatabaseManager("data/signal_flux.db")
tools = SentimentTools(db)

# Auto-score all unanalyzed news (detects language automatically)
updated_count = tools.batch_update_news_sentiment()
print(f"Auto-scored {updated_count} news items")

# Auto-score news from specific source (e.g., CNA)
updated_count = tools.batch_update_news_sentiment(source="cna_finance")
```

**Scoring logic:**
- **Strong positive**: +0.5 (e.g., "創新高", "史上最高値", "record high")
- **Medium positive**: +0.2 (e.g., "上漲", "上昇", "rise")
- **Weak positive**: +0.1 (e.g., "微漲", "小幅上昇", "slightly up")
- **Strong negative**: -0.5 (e.g., "創新低", "史上最安値", "crash")
- **Medium negative**: -0.2 (e.g., "下跌", "下落", "fall")
- **Weak negative**: -0.1 (e.g., "微跌", "小幅下落", "slightly down")
- **Neutral**: 0.0 (e.g., "持平", "横ばい", "update")

**Features:**
- **Language detection**: Automatically detects zh-TW, ja, en from news content
- **Keyword matching**: Saves matched keywords to `meta_data.sentiment_keywords`
- **Batch processing**: Efficiently scores hundreds of news items
- **Extensible**: Add custom keywords by editing JSON files in `references/`

### 2. Manual Sentiment Analysis (Agent-Driven)

For more nuanced analysis, follow these steps:

#### Evaluate Sentiment

Read the text and determine:
- **Positive (+0.1 to +1.0)**: Bullish signals, earnings growth, policy tailwinds, product launches, analyst upgrades
- **Negative (-1.0 to -0.1)**: Bearish signals, losses, sanctions, price drops, analyst downgrades, regulatory risks
- **Neutral (-0.1 to +0.1)**: Factual reporting, consolidation, ambiguous impact

#### Return Structured Result

Always return a JSON object with these fields:

```json
{"score": <float: -1.0 ~ 1.0>, "label": "<positive/negative/neutral>", "reason": "<brief explanation in Traditional Chinese>"}
```

#### Examples

**Positive example:**
> Text: "台積電宣布 2nm 量產時程提前，外資上調目標價至 2000 元。"
> Result: `{"score": 0.5, "label": "positive", "reason": "2nm 量產提前為長期利多，外資上調目標價強化短期看好訊號"}`

**Negative example:**
> Text: "台積電南科廠區火災，產線停工估計影響 3% 產能。"
> Result: `{"score": -0.4, "label": "negative", "reason": "火災導致產線停工，短期產能受損，影響營收與獲利"}`

**Neutral example:**
> Text: "台積電公布 7 月營收，年增 5.2% 符合市場預期。"
> Result: `{"score": 0.0, "label": "neutral", "reason": "營收符合預期，無明顯超預期或不及預期訊號"}`

## Saving Results to Database

### Manual Analysis (Agent-Driven)

```python
from scripts.database_manager import DatabaseManager
from scripts.sentiment_tools import SentimentTools

db = DatabaseManager("data/signal_flux.db")
tools = SentimentTools(db)

# Save manual analysis result
tools.update_single_news_sentiment(news_id, score, reason)
```

### Automated Analysis

```python
from scripts.database_manager import DatabaseManager
from scripts.sentiment_tools import SentimentTools

db = DatabaseManager("data/signal_flux.db")
tools = SentimentTools(db)

# Auto-score a single news item (language auto-detected from meta_data)
tools.auto_score_news(news_item)  # news_item is a dict with id, title, content, meta_data

# Batch auto-score all unanalyzed news
updated_count = tools.batch_update_news_sentiment()

# Batch auto-score news from specific source
updated_count = tools.batch_update_news_sentiment(source="cna_finance")
```

## Keyword Dictionaries

The skill includes comprehensive keyword dictionaries in the `references/` directory:

| Language | File | Keywords Count | Example Keywords |
|----------|------|----------------|-------------------|
| zh-TW    | [keywords_zh_tw.json](references/keywords_zh_tw.json) | 150+ | 創新高, 營收創新高, 大漲, 利多, 擴產, 量產, 併購, AI, 半導體, 電動車 |
| ja       | [keywords_ja.json](references/keywords_ja.json) | 120+ | 最高値, 増収増益, 急騰, 買い越し, 増産, M&A, AI, 半導体, 電気自動車 |
| en       | Built-in | 30+ | record high, surge, bullish, upgrade, acquire, launch |

**Customization:**
You can extend these dictionaries by editing the JSON files. The format is:

```json
{
  "positive": {
    "strong": ["keyword1", "keyword2"],
    "medium": ["keyword3"],
    "weak": ["keyword4"]
  },
  "negative": {
    "strong": ["keyword5"],
    "medium": ["keyword6"],
    "weak": ["keyword7"]
  },
  "neutral": ["keyword8", "keyword9"]
}
```

## Database Schema

The skill updates the `daily_news` table with:
- `sentiment_score`: float (-1.0 ~ +1.0)
- `meta_data`: JSON field containing:
  - `sentiment_reason`: Analysis reason (manual analysis)
  - `sentiment_keywords`: Matched keywords (automated analysis)

## Dependencies

- `sqlite3` (built-in)
- `loguru`

No external ML libraries required.