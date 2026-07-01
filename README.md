# 🧠 Awesome Finance Skills

> 將你的 AI Agent 變身為華爾街分析師。
>
> 一套即插即用的技能套件，為 LLM Agent 注入即時新聞、台股美股行情、情緒分析、邏輯鏈路可視化與市場預測能力。

[English](#english) | [繁體中文](#中文)

---

<a name="english"></a>
## 🇬🇧 English

### What's Inside

| Skill | What It Does |
|:------|:------------|
| **alphaear-news** | Fetches financial news from RSS feeds (CNA, Bloomberg, Reuters, NHK) + Polymarket prediction data |
| **alphaear-stock** | Searches and retrieves stock data — TWSE / TPEx (Taiwan) and US stocks via yfinance |
| **alphaear-sentiment** | Guides the Agent to analyze financial text sentiment (-1.0 ~ +1.0), no external ML models needed |
| **alphaear-search** | Web search (Jina / DuckDuckGo) + local RAG over cached news |
| **alphaear-predictor** | Kronos time-series forecasting with news-aware sentiment adjustments |
| **alphaear-signal-tracker** | Tracks evolution of investment signals — Strengthen / Weaken / Falsify |
| **alphaear-reporter** | Generates professional research reports: Plan → Write → Edit → Charts |
| **alphaear-logic-visualizer** | Converts logic chains into Draw.io XML diagrams |
| **alphaear-composer** | Assembles raw data into `latest.json` — the missing link that turns independent skills into a pipeline |

### How to Use

#### Install a Single Skill

```bash
# Install one skill at a time
npx skills add wolfgangyu/Awesome-finance-skills@alphaear-stock
npx skills add wolfgangyu/Awesome-finance-skills@alphaear-news
```

#### Install All Skills

```bash
git clone https://github.com/wolfgangyu/Awesome-finance-skills.git
cp -r Awesome-finance-skills/skills/* ~/.claude/skills/
```

Then ask your Agent things like:

> "Analyze how the gold crash affects US and Taiwan stocks"
> "Search recent Apple news and tell me the sentiment"

### Architecture

Skills are designed to be **independent** — each one can be installed separately. They share a common database schema (`skills/_shared/alphaear_schema/`) for investment signals, but each skill manages its own SQLite database.

#### Standalone Usage

Each skill works on its own:

```
alphaear-stock  →  stock prices & tickers
alphaear-news   →  aggregated financial news
alphaear-search →  web search + local RAG
alphaear-sentiment →  sentiment scores for news
alphaear-predictor →  Kronos forecasts (uses news + stock data)
alphaear-reporter →  generates research reports (uses everything above)
alphaear-deepear-lite →  fetches signals (local or remote)
```

#### Pipeline Mode (Composer)

Install all data-collecting skills and run `alphaear-composer` to assemble them into a unified signal report:

```
資料層 ──▶ 組裝層 ──▶ 消費層

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ alphaear-news│  │alphaear-     │  │ alphaear-     │
│              │  │search        │  │stock          │
│ RSS 聚合     │  │ 網路搜尋     │  │ 股價資料      │
│ 10+ 來源     │  │ Baidu/Google │  │ TWSE/TPEx/    │
│              │  │              │  │ yfinance      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────┐
│         signal_flux.db (共享 SQLite)             │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐  │
│  │ daily_news  │  │search_detail│  │stock_  │  │
│  │             │  │             │  │prices   │  │
│  │ id, title,  │  │ title, url, │  │        │  │
│  │ content,    │  │ content,    │  │ ticker, │  │
│  │ sentiment   │  │ sentiment   │  │ OHLCV  │  │
│  └─────────────┘  └─────────────┘  └────────┘  │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│       alphaear-composer (組裝廠)                 │
│                                                 │
│  DatabaseMgr ──▶ SignalFormation ──▶ Serializer │
│       │              │                            │
│       │         ISQ Scoring                      │
│       │         sentiment  (-1 ~ +1)             │
│       │         confidence   (0 ~ 1)             │
│       │         intensity    (1 ~ 5)             │
│       │         gap          (0 ~ 1)             │
│       │         timeliness   (0 ~ 1)             │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│              data/latest.json                    │
│                                                  │
│  {                                               │
│    "generated_at": "...",                        │
│    "signals": [                                  │
│      {                                           │
│        "signal_id": "NVDA",                      │
│        "title": "NVDA reaches ATH",              │
│        "sentiment_score": 0.5,                   │
│        "confidence": 0.61,                       │
│        "intensity": 3,                           │
│        "sources": [...],                         │
│        ...                                       │
│      }                                           │
│    ],                                            │
│    "charts": {}                                  │
│  }                                               │
└────────────────────────┬────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
   ┌──────────────────┐   ┌──────────────────────┐
   │ alphaear-deepear-│   │  你的 Vercel 服務     │
   │ lite (--local)   │   │  (可選：自建)          │
   │                  │   │                       │
   │ 讀本機 latest.json│   │ 部署 latest.json 到   │
   │                  │   │  deepear.vercel.app/  │
   └──────────────────┘   └──────────────────────┘
```

**使用方式：**

```bash
# 1. 先收集資料（需要 alphaear-news 等資料收集 skill）
python3 skills/alphaear-news/scripts/news_tools.py  # 抓新聞進 DB

# 2. 組裝成 latest.json
python3 skills/alphaear-composer/scripts/composer.py --days 1 --market both

# 3. 讀取並格式化輸出
python3 skills/alphaear-composer/scripts/composer.py --read
# 或
python3 skills/alphaear-deepear-lite/scripts/deepear_lite.py --local
```

**關鍵設計：**
- composer 是**讀取層**，不修改任何現有 skill 的資料收集邏輯
- `latest.json` 格式跟 DeepEar Vercel 服務**完全一致**，可以互換
- 不需要 LLM 也能跑（heuristic 模式），要更高品質可擴充 LLM 模式

### Related Projects

- **[DeepEar (AlphaEar)](https://github.com/RKiding/AlphaEar)** — Full autonomous financial analysis framework

---

<a name="中文"></a>
## 🇹🇼 繁體中文

### 技能清單

| 技能 | 功能說明 |
|:------|:---------|
| **alphaear-news** | 從 RSS 來源抓取財經新聞（中央社、Bloomberg、Reuters、NHK）+ Polymarket 預測市場 |
| **alphaear-stock** | 搜尋台股（TWSE/TPEx）與美股行情，支援代碼搜尋與歷史 OHLCV |
| **alphaear-sentiment** | 引導 Agent 分析金融文本情緒（-1.0 ~ +1.0），無需額外安裝機器學習模型 |
| **alphaear-search** | 網路搜尋（Jina / DuckDuckGo）+ 本機 RAG 檢索 |
| **alphaear-predictor** | Kronos 時序預測模型，結合新聞情緒動態調整 |
| **alphaear-signal-tracker** | 追蹤投資訊號演化：強化 / 弱化 / 證偽 |
| **alphaear-reporter** | 生成專業研報：規劃 → 撰寫 → 編輯 → 圖表 |
| **alphaear-logic-visualizer** | 將邏輯鏈轉為 Draw.io XML 圖表 |
| **alphaear-composer** | 將分散的資料技能組裝成 `latest.json` — 讓獨立 skills 變成完整 pipeline |

### 如何使用

#### 安裝單一技能

```bash
# 一次安裝一個技能
npx skills add wolfgangyu/Awesome-finance-skills@alphaear-stock
npx skills add wolfgangyu/Awesome-finance-skills@alphaear-news
```

#### 安裝全部技能

```bash
git clone https://github.com/wolfgangyu/Awesome-finance-skills.git
cp -r Awesome-finance-skills/skills/* ~/.claude/skills/
```

接著就可以問你的 Agent：

> "分析貴金屬跳水對美國與台灣股市的影響"
> "搜尋蘋果最新新聞並告訴我情緒是正面還是負面"

### 架構

每個 skill 都是**獨立**的，可以單獨安裝。它們共用一份投資訊號的 schema（`skills/_shared/alphaear_schema/`），但每個 skill 各自管理自己的 SQLite 資料庫。

#### 獨立使用

每個 skill 都可以單獨運作：

```
alphaear-stock  →  個股行情
alphaear-news   →  聚合財經新聞
alphaear-search →  網路搜尋 + 本機 RAG
alphaear-sentiment →  新聞情緒分析
alphaear-predictor →  Kronos 預測（使用新聞 + 行情資料）
alphaear-reporter →  生成研報（整合以上所有技能）
alphaear-deepear-lite →  取得訊號（本機或遠端）
```

#### 串聯模式（Composer）

安裝所有資料收集技能後，執行 `alphaear-composer` 即可將它們組裝成統一的訊號報告：

```
資料層 ──▶ 組裝層 ──▶ 消費層

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ alphaear-news│  │alphaear-     │  │ alphaear-     │
│              │  │search        │  │stock          │
│ RSS 聚合     │  │ 網路搜尋     │  │ 股價資料      │
│ 10+ 來源     │  │ Baidu/Google │  │ TWSE/TPEx/    │
│              │  │              │  │ yfinance      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────┐
│         signal_flux.db (共享 SQLite)             │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐  │
│  │ daily_news  │  │search_detail│  │stock_  │  │
│  │             │  │             │  │prices   │  │
│  │ id, title,  │  │ title, url, │  │        │  │
│  │ content,    │  │ content,    │  │ ticker, │  │
│  │ sentiment   │  │ sentiment   │  │ OHLCV  │  │
│  └─────────────┘  └─────────────┘  └────────┘  │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│       alphaear-composer (組裝廠)                 │
│                                                 │
│  DatabaseMgr ──▶ SignalFormation ──▶ Serializer │
│       │              │                            │
│       │         ISQ Scoring                      │
│       │         sentiment  (-1 ~ +1)             │
│       │         confidence   (0 ~ 1)             │
│       │         intensity    (1 ~ 5)             │
│       │         gap          (0 ~ 1)             │
│       │         timeliness   (0 ~ 1)             │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│              data/latest.json                    │
│                                                  │
│  {                                               │
│    "generated_at": "...",                        │
│    "signals": [                                  │
│      {                                           │
│        "signal_id": "NVDA",                      │
│        "title": "NVDA reaches ATH",              │
│        "sentiment_score": 0.5,                   │
│        "confidence": 0.61,                       │
│        "intensity": 3,                           │
│        "sources": [...],                         │
│        ...                                       │
│      }                                           │
│    ],                                            │
│    "charts": {}                                  │
│  }                                               │
└────────────────────────┬────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
   ┌──────────────────┐   ┌──────────────────────┐
   │ alphaear-deepear-│   │  你的 Vercel 服務     │
   │ lite (--local)   │   │  (可選：自建)          │
   │                  │   │                       │
   │ 讀本機 latest.json│   │ 部署 latest.json 到   │
   │                  │   │  deepear.vercel.app/  │
   └──────────────────┘   └──────────────────────┘
```

**使用方式：**

```bash
# 1. 先收集資料（需要 alphaear-news 等資料收集 skill）
python3 skills/alphaear-news/scripts/news_tools.py  # 抓新聞進 DB

# 2. 組裝成 latest.json
python3 skills/alphaear-composer/scripts/composer.py --days 1 --market both

# 3. 讀取並格式化輸出
python3 skills/alphaear-composer/scripts/composer.py --read
# 或
python3 skills/alphaear-deepear-lite/scripts/deepear_lite.py --local
```

**關鍵設計：**
- composer 是**讀取層**，不修改任何現有 skill 的資料收集邏輯
- `latest.json` 格式跟 DeepEar Vercel 服務**完全一致**，可以互換
- 不需要 LLM 也能跑（heuristic 模式），要更高品質可擴充 LLM 模式

### 相關專案

- **[DeepEar (AlphaEar)](https://github.com/RKiding/AlphaEar)** — 完整的自動化金融分析框架

