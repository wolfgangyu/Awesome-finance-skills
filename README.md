# 🧠 Awesome Finance Skills

> 將你的 AI Agent 變身為金融分析師。
>
> 一套即插即用的**獨立技能套件**，為 LLM Agent 注入即時新聞、台股美股行情、情緒分析、邏輯鏈路可視化與市場預測能力。

[English](#english) | [繁體中文](#中文)

---

<a name="english"></a>
## 🇬🇧 English

### 🚀 Project Status
This project was originally forked from [RKiding/AlphaEar](https://github.com/RKiding/AlphaEar), but has since evolved into an independent repository with significant improvements and new features. The fork status has been removed.

Key differences from the original:
- Added new skills: `alphaear-reporter`, `alphaear-deepear-lite`, `alphaear-logic-visualizer`
- Removed dependencies: `akshare`, `EastMoneyDirect`, BERT/FinBERT models
- Improved multi-language sentiment analysis (zh-TW/ja/en)
- Each skill manages its own SQLite database for better modularity

---

### What's Inside

| Skill | What It Does |
|:------|:------------|
| **alphaear-news** | Fetches financial news from RSS feeds (CNA, Bloomberg, Reuters, NHK) + Polymarket prediction data |
| **alphaear-stock** | Searches and retrieves stock data — TWSE/TPEx (Taiwan) and US stocks via yfinance |
| **alphaear-sentiment** | Keyword-based sentiment analysis for financial text (-1.0 ~ +1.0), supports zh-TW/ja/en |
| **alphaear-search** | Web search (Jina/DuckDuckGo) + local RAG over cached news |
| **alphaear-predictor** | Kronos time-series forecasting with news-aware sentiment adjustments |
| **alphaear-signal-tracker** | Tracks evolution of investment signals — Strengthen/Weaken/Falsify |
| **alphaear-reporter** | Generates professional research reports with unified design (CLI/Python API/Agent support) |
| **alphaear-logic-visualizer** | Converts logic chains into Draw.io XML diagrams |
| **alphaear-deepear-lite** | Lightweight DeepEar signal fetcher (local or remote) |

---

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

Then ask your Agent:

> "Analyze how the gold crash affects US and Taiwan stocks"
> "Search recent Apple news and tell me the sentiment"
> "Generate a research report about TSMC's latest earnings"

---

### Architecture

Skills are designed to be **independent** — each one can be installed separately. They share a common database schema (`skills/_shared/alphaear_schema/`) for investment signals, but each skill manages its own SQLite database.

#### Standalone Usage

Each skill works on its own:

```
alphaear-stock  →  stock prices & tickers (TWSE/TPEx/yfinance)
alphaear-news   →  aggregated financial news (10+ sources)
alphaear-search →  web search + local RAG
alphaear-sentiment →  text sentiment (-1.0 ~ +1.0)
alphaear-predictor →  Kronos time-series forecasting
alphaear-signal-tracker →  InvestmentSignal lifecycle (strengthen/weaken/falsify)
alphaear-reporter →  research reports (composes all above)
alphaear-logic-visualizer →  Draw.io XML diagrams
alphaear-deepear-lite →  lightweight DeepEar signal fetcher
```

#### Pipeline Mode

Install all data-collecting skills and use them together:

```
資料層 ──▶ 分析層 ──▶ 報告層

┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│ alphaear-news│  │alphaear-     │  │ alphaear-        │
│              │  │search        │  │stock             │
│ RSS 聚合     │  │ 網路搜尋     │  │ 股價資料         │
│ 10+ 來源     │  │ Baidu/Google │  │ TWSE/TPEx/       │
│              │  │              │  │ yfinance         │
└──────┬───────┘  └──────┬───────┘  └──────┬─────────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────┐
│         signal_flux.db (SQLite)                 │
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
│               alphaear-reporter                 │
│                                                 │
│  Generates professional research reports        │
│  with sentiment analysis and market insights    │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│               Output Formats                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │ Markdown    │  │ JSON       │  │ LINE    │  │
│  │             │  │            │  │ Friendly│  │
│  └─────────────┘  └─────────────┘  └─────────┘  │
└─────────────────────────────────────────────────┘
```

**Key Features:**
- **Multi-market support**: Taiwan (TWSE/TPEx) and US stocks
- **Multi-language support**: zh-TW, ja, en
- **Multi-format output**: Markdown, JSON, LINE-friendly text
- **LLM abstraction**: Supports Anthropic, OpenAI, Gemini
- **No heavy ML models**: Uses keyword-based sentiment analysis

---

<a name="中文"></a>
## 🇹🇼 繁體中文

### 🚀 專案現況
本專案最初 Fork 自 [RKiding/AlphaEar](https://github.com/RKiding/AlphaEar)，但已經獨立發展並移除 Fork 狀態。目前專案新增了多個技能（如 `alphaear-reporter`、`alphaear-deepear-lite`），並移除了 `akshare` 和 `EastMoneyDirect` 等依賴。

主要差異：
- 新增技能：`alphaear-reporter`、`alphaear-deepear-lite`、`alphaear-logic-visualizer`
- 移除依賴：`akshare`、`EastMoneyDirect`、BERT/FinBERT 模型
- 改進多語言情感分析（繁體中文/日文/英文）
- 每個技能管理自己的 SQLite 資料庫，提升模組化

---

### 技能清單

| 技能 | 功能說明 |
|:------|:---------|
| **alphaear-news** | 從 RSS 來源抓取財經新聞（中央社、Bloomberg、Reuters、NHK）+ Polymarket 預測市場 |
| **alphaear-stock** | 搜尋台股（TWSE/TPEx）與美股行情，支援代碼搜尋與歷史 K 線 |
| **alphaear-sentiment** | 關鍵字情緒分析（-1.0 ~ +1.0），支援繁體中文/日文/英文 |
| **alphaear-search** | 網路搜尋（Jina/DuckDuckGo）+ 本機 RAG 檢索 |
| **alphaear-predictor** | Kronos 時序預測模型，結合新聞情緒動態調整 |
| **alphaear-signal-tracker** | 追蹤投資訊號演化：強化/弱化/證偽 |
| **alphaear-reporter** | 生成專業研報，支援 CLI/Python API/Agent 三種模式 |
| **alphaear-logic-visualizer** | 將邏輯鏈轉為 Draw.io XML 圖表 |
| **alphaear-deepear-lite** | 輕量化 DeepEar 訊號抓取工具（本機或遠端） |

---

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
> "搜尋蘋果最新新聞並告訴我情緒分數"
> "生成一份台積電最新財報的研究報告"

---

### 架構

每個 skill 都是**獨立**的，可以單獨安裝。它們共用一份投資訊號的 schema（`skills/_shared/alphaear_schema/`），但每個 skill 各自管理自己的 SQLite 資料庫。

#### 獨立使用

每個技能都可以單獨運作：

```
alphaear-stock  →  個股行情（台股/美股）
alphaear-news   →  聚合財經新聞（10+來源）
alphaear-search →  網路搜尋 + 本機 RAG
alphaear-sentiment →  新聞情緒分析（-1.0 ~ +1.0）
alphaear-predictor →  Kronos 預測模型
alphaear-signal-tracker →  投資訊號追蹤（強化/弱化/證偽）
alphaear-reporter →  生成研報（整合以上所有技能）
alphaear-logic-visualizer →  邏輯鏈可視化（Draw.io）
alphaear-deepear-lite →  輕量化 DeepEar 訊號抓取
```

#### 串聯模式

安裝多個技能後，可以組合使用：

```
資料層 ──▶ 分析層 ──▶ 報告層

┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│ alphaear-news│  │alphaear-     │  │ alphaear-        │
│              │  │search        │  │stock             │
│ RSS 聚合     │  │ 網路搜尋     │  │ 股價資料         │
│ 10+ 來源     │  │ Baidu/Google │  │ TWSE/TPEx/       │
│              │  │              │  │ yfinance         │
└──────┬───────┘  └──────┬───────┘  └──────┬─────────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────┐
│         signal_flux.db (SQLite)                 │
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
│               alphaear-reporter                 │
│                                                 │
│  生成專業研報，包含情緒分析與市場洞察          │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│               輸出格式                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │ Markdown    │  │ JSON       │  │ LINE    │  │
│  │             │  │            │  │ 友好格式│  │
│  └─────────────┘  └─────────────┘  └─────────┘  │
└─────────────────────────────────────────────────┘
```

**關鍵特色：**
- **多市場支援**：台灣（TWSE/TPEx）與美國股市
- **多語言支援**：繁體中文、日文、英文
- **多格式輸出**：Markdown、JSON、LINE 友好格式
- **LLM 抽象介面**：支援 Anthropic、OpenAI、Gemini
- **無重量級模型**：使用關鍵字情緒分析，無需額外安裝 ML 模型