

## 新增功能：統一設計與多場景支援

本次更新實現了 alphaear-reporter 的統一設計，支援三種使用場景：

### 1. CLI 介面（供 Hermes Agent 呼叫）

```bash
# 基本用法
python -m skills.alphaear-reporter.scripts.report_cli \
  --signals '[{"title": "台積電營收", "content": "...", "ticker": "2330.TW"}]' \
  --output line

# 可用參數
--signals    輸入訊號的 JSON 字串（必填）
--market     市場類型 (tw/us/both, 預設: tw)
--output     輸出格式 (markdown/json/line, 預設: markdown)
--no-llm     禁用 LLM 驅動邏輯，使用簡化邏輯
--debug      啟用除錯模式
```

### 2. Python API（供 Polaris 後端 import）

```python
from skills.alphaear-reporter.scripts.report_api import ReportAPI

# 生成 LINE 官方帳號友好報告
line_report = await ReportAPI.generate_report_for_line(signals, market="tw")

# 生成 LIFF 網頁用 HTML 報告
liff_report = await ReportAPI.generate_report_for_liff(signals, market="tw")

# 生成 Hermes Agent 相容格式
hermes_report = await ReportAPI.generate_report_for_hermes(signals, market="tw")
```

### 3. 相容現有 Agentic Workflow（供 Claude Code 使用）

```python
from skills.alphaear-reporter.scripts.report_agent import ReportAgent

# 保持現有介面不變
agent = ReportAgent(db)
report = await agent.generate_report(signals, market="tw")
```

### 4. 核心元件：ReportGenerator

所有場景共用同一個核心邏輯實作，支援：
- **簡化邏輯**（無 LLM）：快速聚類別和報告生成
- **LLM 驅動邏輯**：深度分析和智能撰寫
- **統一輸出格式**：Markdown、JSON、LINE 友好格式
- **市場相容性**：台灣（tw）、美國（us）、台美（both）

```python
from skills.alphaear-reporter.scripts.report_generator import ReportGenerator

generator = ReportGenerator(db, llm_client=llm_client, market="tw")
report = await generator.generate_report(signals, use_llm=True)
```

### 5. LLM 抽象介面

新增 `LLMClient` 抽象介面，允許外部注入不同 LLM 後端：

```python
from skills.alphaear-reporter.scripts.utils.llm.base_client import LLMClient

class CustomLLMClient(LLMClient):
    async def generate(self, prompt, json_mode=False, temperature=0.7, max_tokens=4096):
        # 自定義 LLM 實作
        return "..."
```

### 6. 輸出格式說明

| 格式 | 用途 | 特點 |
|------|------|------|
| `markdown` | 通用報告格式 | 完整 Markdown 格式，包含標題、章節、參考文獻 |
| `json` | 前端渲染 | 結構化 JSON，便於前端解析和渲染 |
| `line_friendly` | LINE 官方帳號 | 簡化純文字格式，適合 LINE 訊息限制 |

### 7. 使用範例

**Hermes Agent 呼叫範例**
```bash
python -m skills.alphaear-reporter.scripts.report_cli \
  --signals '[{"title": "台積電營收創新高", "content": "台積電公布 7 月營收創歷史新高...", "ticker": "2330.TW"}]' \
  --market tw \
  --output line \
  --no-llm
```

**Polaris 後端呼叫範例**
```python
from skills.alphaear-reporter.scripts.report_api import ReportAPI

signals = [{"title": "台積電營收", "content": "...", "ticker": "2330.TW"}]

# 發送到 LINE 官方帳號
line_message = await ReportAPI.generate_report_for_line(signals, market="tw")

# 嵌入 LIFF 網頁
liff_html = await ReportAPI.generate_report_for_liff(signals, market="tw")
```

**Claude Code 呼叫範例**
```python
from skills.alphaear-reporter.scripts.report_agent import ReportAgent

agent = ReportAgent(db)
report = await agent.generate_report(signals, market="tw")
```