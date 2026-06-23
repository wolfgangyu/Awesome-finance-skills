# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案本質

**Awesome Finance Skills** 是一個「技能套件集合」，不是單一應用。

- 每個 `skills/<skill-name>/` 是獨立、可散佈的 Agent skill（OpenAI/Claude/Agno 框架皆可載入）。
- 每個 skill 帶有 `SKILL.md`（YAML frontmatter `name`+`description` + Markdown body）以及可選的 `scripts/`、`references/`、`assets/` 資源。
- 使用者透過 `npx skills add RKiding/Awesome-finance-skills@<skill-name>` 安裝單一 skill，或把整個 `skills/*` 複製到 OpenCode/Claude/Codex 的 skill 目錄（參考 README 表格）。
- 上游完整框架是 [DeepEar (AlphaEar)](https://github.com/RKiding/AlphaEar)，本倉庫是「拆解後的 skill 切片」。

## 重要：CWD 與 import path 慣例

> 這個集合的 scripts 子目錄佈局並不一致，未來修改時容易踩雷，務必看清。

每個 skill 下的 `scripts/` 兩種佈局並存：

| 類型 | 套件 | 佈局 |
|:-----|:-----|:-----|
| 「flat」 | `alphaear-news`, `alphaear-stock`, `alphaear-sentiment`, `alphaear-search`, `alphaear-deepear-lite`, `alphaear-logic-visualizer` | `scripts/<tool>.py`, `scripts/database_manager.py`，模組內用 `from .database_manager import DatabaseManager` |
| 「nested」 | `alphaear-predictor`, `alphaear-signal-tracker`, `alphaear-reporter` | `scripts/*.py` 是 entry / agent，`scripts/{utils,prompts,schema,tools,predictor}/` 才是實作；模組間用 `from .utils.xxx` |

SKILL.md 範例與 `tests/` 目錄的 import 都各自反映自家佈局。修改任何子模組時，先 `ls <skill>/scripts/` 確認是 flat 還是 nested。

## 添加或修改 skill 的標準流程

來自 `skills/skill-creator/SKILL.md` 的硬性規則：

1. **命名**：`name` 必須是 lowercase+digits+hyphens，≤ 64 字元，不可以開頭/結尾 `-`、不可 `--`。
2. **Frontmatter**：YAML 欄位只能用 `name, description, license, allowed-tools, metadata`（驗證腳本會擋）。
3. **描述即觸發器**：`description` 是 skill 被載入的唯一依據，需含「做什麼 + 何時用」，「When to use」不要寫到 body 內。
4. **Body ≤ 500 行**；過長的 API、schema、prompt 範例移到 `references/` 並在 SKILL.md 連結。
5. **不允許**額外 README/CHANGELOG 等輔助文件（只留 SKILL.md + 真的有用的 resources）。
6. **每個 skill 必須含 `SKILL.md`**（這是 package_skill 驗證的硬條件）。

建立流程：
```bash
# 1. 產出模板
python skills/skill-creator/scripts/init_skill.py <skill-name> --path skills [--resources scripts,references,assets] [--examples]

# 2. 編寫 SKILL.md + resources

# 3. 驗證 + 打包（會自動跑 quick_validate.py）
python skills/skill-creator/scripts/package_skill.py skills/<skill-name> [輸出目錄]
# 產出 <skill-name>.skill（其實是 zip，便於 npx skills 等管道發佈）
```

## 開發常用指令

```bash
# 跑某一個 skill 的測試（從 skill 目錄加入 sys.path，使用 unittest）
python tests/alphaear-news/test_news.py        # 或 -m unittest
python tests/alphaear-stock/test_stock.py
python tests/alphaear-predictor/test_predictor.py
python tests/alphaear-reporter/test_reporter.py
python skills/alphaear-signal-tracker/tests/test_tracker.py
python skills/alphaear-logic-visualizer/tests/test_visualizer.py

# DeepEar Lite 連線煙霧測試
python skills/alphaear-deepear-lite/scripts/deepear_lite.py

# 驗證 + 打包某個 skill
python skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
python skills/skill-creator/scripts/package_skill.py skills/<skill-name>

# 找新聞 source 對應 ID
cat skills/alphaear-news/references/sources.md
```

每個測試的通例：`scripts.xxx_tools` 是 entry class、`scripts.database_manager` 提供 SQLite（預設路徑 `data/signal_flux.db`，測試常用 `DatabaseManager(":memory:")`）。

## 架構與 skill 職責地圖

依資料流由下到上：

| Skill | 角色 | 關鍵 entry | 對外依賴 |
|:------|:-----|:-----------|:---------|
| **alphaear-news** | 多源熱點新聞聚合 + Polymarket 預測市場 | `scripts/news_tools.py::NewsNowTools` | NewsNow API (`https://newsnow.busiyi.world/api/s?id=<id>`)、Jina 內容萃取、Polymarket |
| **alphaear-stock** | 台股（TWSE/TPEx）/ 美股代碼搜尋與歷史 OHLCV | `scripts/stock_tools.py::StockTools`（內含 `TWSEClient` 從 `scripts/twse_client.py` 提供 TWSE/TPEx fallback） | yfinance、requests、pandas |
| **alphaear-sentiment** | FinBERT / LLM 情緒分析（-1.0 ~ +1.0） | `scripts/sentiment_tools.py::SentimentTools` | FinBERT、LLM（Gemini/Anthropic/OpenAI router 在 `scripts/llm/`） |
| **alphaear-search** | Web 搜尋（Jina / DDG / Baidu）+ 本地 RAG | `scripts/search_tools.py::SearchTools` | duckduckgo-search、requests、`hybrid_search.py`（搜 `daily_news` 表） |
| **alphaear-deepear-lite** | 從 `deepear.vercel.app/latest.json` 拉最新訊號 | `scripts/deepear_lite.py::DeepEarLiteTools` | 純 HTTP，無 DB |
| **alphaear-predictor** | Kronos 時序預測 + 新聞情緒調整 | `scripts/forecast_agent.py::ForecastUtils` → `kronos_predictor.KronosPredictorUtility` | torch、transformers、sentence-transformers；模型放在 `exports/models/`，**只接受 `kronos_news_*.pt` 模式 + `weights_only=True`** |
| **alphaear-signal-tracker** | 追蹤既有 `InvestmentSignal` 的演化（強化/弱化/證偽） | `scripts/fin_agent.py::FinAgent` | 內部呼叫 search + stock 工具；agentic，靠 `references/PROMPTS.md` 三段 prompt（FinResearcher → FinAnalyst → Signal Tracking） |
| **alphaear-reporter** | 規劃→撰寫→編輯 → 圖表的研報流程 | `scripts/report_agent.py::ReportAgent`、`scripts/visualizer.py::VisualizerTools` | 內部組合：news + sentiment + stock + search + logic-visualizer |
| **alphaear-logic-visualizer** | 將邏輯鏈轉成 Draw.io XML 並輸出 HTML | `scripts/visualizer.py::render_drawio_to_html` | 標準庫；prompt 在 `references/PROMPTS.md` |
| **skill-creator** | 上面說的，建立/驗證/打包 skill 的工具集 | `scripts/{init_skill, package_skill, quick_validate}.py` | pyyaml |

## 跨 skill 的共享抽象

- **資料模型（核心）**：見 `skills/alphaear-predictor/scripts/schema/models.py`（`InvestmentSignal`、`TransmissionNode`、`ForecastResult`、`KLinePoint`、`ResearchContext`、`InvestmentReport`、`FilterResult`、`SignalCluster`）。其它 skill（reporter、signal-tracker）的 `schema/` 大多重複同一份 schema，**改 schema 時要同步 3 處**。
- **資料庫**：每個 skill 各自宣告 `DatabaseManager` 路徑 `data/signal_flux.db`，表結構 (`daily_news` / `search_cache` / `search_detail` / 行情表等) 在各 skill 的 `scripts/database_manager.py` 中分散維護（這是有意保持 skill 獨立可裝）。要新增 DB 欄位時，傾向在原 skill 內補 `ALTER TABLE` 容錯新增（predictor 版本內可見此模式），而非強耦合單一 migration。
- **LLM 抽象層**：`scripts/llm/{router,factory,capability}.py`，按能力路由到 Anthropic / OpenAI / Gemini（等）。`alphaear-search` 與 `alphaear-sentiment` 共用這層；reporter/signal-tracker 用自己的 utils 變體。

## 安全注意事項

- `alphaear-predictor` 的 SKILL.md 標註 **CAUTION**：Kronos 權重只從 `exports/models/` 載入，且鎖定 `kronos_news_*.pt` pattern + `weights_only=True`。新增權重時務必遵守，不要把任意 `.pt` 放進去。
- 美股行情走 `yfinance`，README 提到台灣用戶可能需要 `HTTP_PROXY` / `HTTPS_PROXY` 環境變數。

## 測試與驗證

`tests/<skill>/` 目錄是各 skill 的 smoke test，目前只驗證 import / class 初始化（預期 LLM / 模型沒到位時會 fail-soft）。重 model 與重網路（`alphaear-predictor` 載 Kronos、`alphaear-stock` 連 yfinance/TWSE/TPEx）我這邊環境通常不會跑通，因此：
- 修改 schema 或 contracts 時，跑對應的 `tests/<skill>/test_*.py` 看 import 階段有沒有炸。
- 需要實際連網/重 model 的功能改動，建議 staging 環境或人工驗證；不要宣稱「通過」。

## 觀察與修復的模式

- SKILL.md body 重複標題（例如 `alphaear-predictor` 有兩個 `### 1. Forecast Market Trends`）— 新增能力章節時檢查是否已存在。
- SKILL.md 範例程式和實際 import path 不完全一致時，優先信實際檔案位置（看 `ls <skill>/scripts/`）。
- `signal-tracker` 目前 SKILL 直說「目前是從 FinAgent 抽出來的 pattern，未來重構為 standalone」，修改前先看 `scripts/fin_agent.py::track_signal` 實作。
