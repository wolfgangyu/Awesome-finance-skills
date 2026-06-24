# 🧠 Awesome Finance Skills

> **Transform your AI agent into a Wall Street analyst in seconds.**
>
> A plug-and-play skill collection that empowers LLMs with **real-time news**, **stock data**, **sentiment analysis**, **logic visualization**, and **market prediction** capabilities.
>
> 🚀 **New:** [DeepEar](https://github.com/HKUSTDial/DeepEar) Live Demo (Free Lite Version) is now online: [https://deepear.vercel.app/](https://deepear.vercel.app/)

[English](#english) | [繁體中文](#繁體中文)

---

<a name="english"></a>
## 🇬🇧 English

### ✨ Highlights

| 📰 Real-time News & Trends | 📊 Logic Chain Visualization | 🔮 AI-Powered Prediction |
|:---:|:---:|:---:|
| ![News Analysis](figs/news.png) | ![Logic Chain](figs/logic.png) | ![Prediction](figs/predict.png) |
| Aggregate hot news from 10+ sources (Cailian, WSJ, Weibo, Polymarket...) | Auto-generate transmission chain diagrams explaining market impact | Kronos model forecasts with news-aware adjustments |

### 🚀 Quick Start

#### Option 1: One-Step Install (Recommended)
You can now install individual skills directly using `npx skills`:

```bash
# Install a specific skill (e.g., alphaear-news)
npx skills add RKiding/Awesome-finance-skills@alphaear-news

# Or search for all the skills and then select one
npx skills find "alphaear"
```

#### Option 2: Manual Installation
```bash
# Clone the repository
git clone https://github.com/RKiding/Awesome-finance-skills.git

# Copy skills to your agent (example for OpenCode)
cp -r Awesome-finance-skills/skills/* ~/.config/opencode/skills/
```

**That's it!** Your agent now understands finance. Try asking:

> *"Analyze how the gold crash affects US and Taiwan stocks"*

🔗 **Live Demo**: [See it in action →](https://opncd.ai/share/wOp37QIs)

---

### 📦 Included Skills

| Skill | Description | Key Feature |
|:------|:------------|:------------|
| **alphaear-news** | Real-time financial news & trends | 10+ sources, Polymarket data |
| **alphaear-stock** | US and Taiwan (TWSE/TPEx) stock data | Ticker search, OHLCV, Fundamentals |
| **alphaear-sentiment** | FinBERT / LLM sentiment analysis | Score: -1.0 ~ +1.0 |
| **alphaear-predictor** | Kronos time-series forecasting | News-aware adjustments |
| **alphaear-signal-tracker** | Investment signal evolution | Strengthen / Weaken / Falsify |
| **alphaear-logic-visualizer** | Transmission chain diagrams | Draw.io XML output |
| **alphaear-reporter** | Professional report generation | Plan → Write → Edit → Chart |
| **alphaear-search** | Web search & local RAG | Jina / DDG / Baidu |

---

### 🔧 Integration Guide

**Awesome Finance Skills** supports multiple agent frameworks:

| Framework | Scope | Installation Path |
|:----------|:------|:------------------|
| **Antigravity** | Workspace | `<workspace>/.agent/skills/<skill>/` |
| | Global | `~/.gemini/antigravity/global_skills/<skill>/` |
| **OpenCode** | Project | `.opencode/skills/<skill>/` or `.claude/skills/<skill>/` |
| | Global | `~/.config/opencode/skills/<skill>/` |
| **OpenClaw** | Workspace | `<workspace>/skills` (highest priority) |
| | Managed | `~/.openclaw/skills` |
| **Claude Code / Codex** | Personal | `~/.claude/skills/` or `~/.codex/skills/` |
| | Project | `.claude/skills/` |

> 💡 Each skill folder must contain a `SKILL.md` file.

---

### 🔗 Related Project

For a **complete autonomous financial analysis framework**, check out:

**[DeepEar →](https://github.com/RKiding/AlphaEar)**

---

<a name="中文"></a>
## 🇹🇼 繁體中文

> 🚀 **全新：** [DeepEar](https://github.com/HKUSTDial/DeepEar) 線上演示（免費 Lite 版）現已上線：[https://deepear.vercel.app/](https://deepear.vercel.app/)

### ✨ 核心亮點

| 📰 即時新聞聚合 | 📊 邏輯鏈路可視化 | 🔮 AI 智能預測 |
|:---:|:---:|:---:|
| ![新聞分析](figs/news.png) | ![邏輯鏈路](figs/logic.png) | ![預測分析](figs/predict.png) |
| 聚合財聯社、華爾街見聞、微博、Polymarket 等 10+ 信源 | 自動生成傳導鏈路圖，直觀解釋市場影響 | 基於 Kronos 模型的時序預測，結合新聞情緒動態調整 |

### 🚀 快速開始

#### 方式一：一鍵安裝（推薦）
現在你可以使用 `npx skills` 直接安裝單個技能：

```bash
# 安裝指定技能（例如：alphaear-news）
npx skills add RKiding/Awesome-finance-skills@alphaear-news

# 或者搜尋更多金融技能
npx skills find "alphaear"
```

#### 方式二手動安裝
```bash
# 複製倉庫
git clone https://github.com/RKiding/Awesome-finance-skills.git

# 複製技能到你的 Agent（以 OpenCode 為例）
cp -r Awesome-finance-skills/skills/* ~/.config/opencode/skills/
```

**搞定！** 你的 Agent 現在已具備金融分析能力。試試問它：

> *"分析貴金屬跳水對美國與台灣股市的影響"*

🔗 **線上演示**：[查看實戰效果 →](https://opncd.ai/share/wOp37QIs)

---

### 📦 技能清單

| 技能 | 功能描述 | 核心特性 |
|:-----|:---------|:---------|
| **alphaear-news** | 即時財經新聞與熱點趨勢 | 10+ 信源，Polymarket 資料 |
| **alphaear-stock** | 美國與台灣（TWSE/TPEx）股市行情與基本面 | 股票搜尋、OHLCV、個股基本面 |
| **alphaear-sentiment** | FinBERT / LLM 情感分析 | 評分範圍：-1.0 ~ +1.0 |
| **alphaear-predictor** | Kronos 時序預測模型 | 結合新聞情緒動態調整 |
| **alphaear-signal-tracker** | 投資訊號演化追蹤 | 強化 / 弱化 / 證偽 |
| **alphaear-logic-visualizer** | 傳導鏈路圖生成 | 輸出 Draw.io XML |
| **alphaear-reporter** | 專業研報生成 | 規劃 → 撰寫 → 編輯 → 圖表 |
| **alphaear-search** | 全網搜尋與本機 RAG | 支援 Jina / DDG / 百度 |

---

### 🔧 技能接入指南

**Awesome Finance Skills** 支援多種主流 Agent 框架：

| 框架 | 作用域 | 安裝路徑 |
|:-----|:-------|:---------|
| **Antigravity** | 工作區 | `<workspace>/.agent/skills/<skill>/` |
| | 全域 | `~/.gemini/antigravity/global_skills/<skill>/` |
| **OpenCode** | 專案 | `.opencode/skills/<skill>/` 或 `.claude/skills/<skill>/` |
| | 全域 | `~/.config/opencode/skills/<skill>/` |
| **OpenClaw** | 工作區 | `<workspace>/skills`（優先級最高） |
| | 託管 | `~/.openclaw/skills` |
| **Claude Code / Codex** | 個人 | `~/.claude/skills/` 或 `~/.codex/skills/` |
| | 專案 | `.claude/skills/` |

> 💡 每個技能資料夾需套件含 `SKILL.md` 檔案。

---

### 🔗 完整框架

如需**完整的自動化金融分析框架**，請關注：

**[DeepEar →](https://github.com/RKiding/AlphaEar)**

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=RKiding/Awesome-finance-skills&type=Date)](https://star-history.com/#RKiding/Awesome-finance-skills&Date)
