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
| **alphaear-news** | Aggregates hot financial news from 10+ sources (Cailian, Wallstreetcn, Xueqiu, Polymarket...) |
| **alphaear-stock** | Searches and retrieves stock data — TWSE / TPEx (Taiwan) and US stocks via yfinance |
| **alphaear-sentiment** | Guides the Agent to analyze financial text sentiment (-1.0 ~ +1.0), no external ML models needed |
| **alphaear-search** | Web search (Jina / DuckDuckGo) + local RAG over cached news |
| **alphaear-predictor** | Kronos time-series forecasting with news-aware sentiment adjustments |
| **alphaear-signal-tracker** | Tracks evolution of investment signals — Strengthen / Weaken / Falsify |
| **alphaear-reporter** | Generates professional research reports: Plan → Write → Edit → Charts |
| **alphaear-logic-visualizer** | Converts logic chains into Draw.io XML diagrams |
| **alphaear-deepear-lite** | Lightweight fetcher for DeepEar market signals |

### How to Use

#### Install a Single Skill

```bash
# Install one skill at a time
npx skills add RKiding/Awesome-finance-skills@alphaear-stock
npx skills add RKiding/Awesome-finance-skills@alphaear-news
```

#### Install All Skills

```bash
git clone https://github.com/RKiding/Awesome-finance-skills.git
cp -r Awesome-finance-skills/skills/* ~/.claude/skills/
```

Then ask your Agent things like:

> "Analyze how the gold crash affects US and Taiwan stocks"
> "Search recent Apple news and tell me the sentiment"

### Architecture

Skills are designed to be **independent** — each one can be installed separately. They share a common database schema (`skills/_shared/alphaear_schema/`) for investment signals, but each skill manages its own SQLite database.

Data flows bottom-up:

```
alphaear-stock  →  stock prices & tickers
alphaear-news   →  aggregated financial news
alphaear-search →  web search + local RAG
alphaear-sentiment →  sentiment scores for news
alphaear-predictor →  Kronos forecasts (uses news + stock data)
alphaear-reporter →  generates research reports (uses everything above)
```

### Related Projects

- **[DeepEar (AlphaEar)](https://github.com/RKiding/AlphaEar)** — Full autonomous financial analysis framework
- **[SKILL.md spec](https://github.com/anthropics/claude-code/tree/main/src/skills)** — Skill format specification

---

<a name="中文"></a>
## 🇹🇼 繁體中文

### 技能清單

| 技能 | 功能說明 |
|:------|:---------|
| **alphaear-news** | 聚合 10+ 信源的財經熱點新聞（財聯社、華爾街見聞、雪球、Polymarket...） |
| **alphaear-stock** | 搜尋台股（TWSE/TPEx）與美股行情，支援代碼搜尋與歷史 OHLCV |
| **alphaear-sentiment** | 引導 Agent 分析金融文本情緒（-1.0 ~ +1.0），無需額外安裝機器學習模型 |
| **alphaear-search** | 網路搜尋（Jina / DuckDuckGo）+ 本機 RAG 檢索 |
| **alphaear-predictor** | Kronos 時序預測模型，結合新聞情緒動態調整 |
| **alphaear-signal-tracker** | 追蹤投資訊號演化：強化 / 弱化 / 證偽 |
| **alphaear-reporter** | 生成專業研報：規劃 → 撰寫 → 編輯 → 圖表 |
| **alphaear-logic-visualizer** | 將邏輯鏈轉為 Draw.io XML 圖表 |
| **alphaear-deepear-lite** | 輕量版 DeepEar 訊號取得工具 |

### 如何使用

#### 安裝單一技能

```bash
# 一次安裝一個技能
npx skills add RKiding/Awesome-finance-skills@alphaear-stock
npx skills add RKiding/Awesome-finance-skills@alphaear-news
```

#### 安裝全部技能

```bash
git clone https://github.com/RKiding/Awesome-finance-skills.git
cp -r Awesome-finance-skills/skills/* ~/.claude/skills/
```

接著就可以問你的 Agent：

> "分析貴金屬跳水對美國與台灣股市的影響"
> "搜尋蘋果最新新聞並告訴我情緒是正面還是負面"

### 架構

每個 skill 都是**獨立**的，可以單獨安裝。它們共用一份投資訊號的 schema（`skills/_shared/alphaear_schema/`），但每個 skill 各自管理自己的 SQLite 資料庫。

資料流向由下到上：

```
alphaear-stock  →  個股行情
alphaear-news   →  聚合財經新聞
alphaear-search →  網路搜尋 + 本機 RAG
alphaear-sentiment →  新聞情緒分析
alphaear-predictor →  Kronos 預測（使用新聞 + 行情資料）
alphaear-reporter →  生成研報（整合以上所有技能）
```

### 相關專案

- **[DeepEar (AlphaEar)](https://github.com/RKiding/AlphaEar)** — 完整的自動化金融分析框架
- **[SKILL.md 規範](https://github.com/anthropics/claude-code/tree/main/src/skills)** — 技能格式規格
