# AlphaEar Reporter 統一設計實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 實作 `alphaear-reporter` skill 的統一設計，支援 Claude Code、Hermes Agent、Polaris 前端三種使用場景

**Architecture:** 核心邏輯抽象化 + 多進入點設計。`ReportGenerator` 負責核心邏輯，`report_cli.py`/`report_api.py`/`report_agent.py` 提供不同進入點

**Tech Stack:** Python 3.10+, SQLite, LLM (Anthropic/OpenAI/Gemini), CLI (argparse), Markdown/JSON 處理

## Global Constraints

- **Python 版本**：3.10+（相容現有程式碼）
- **相依套件**：`loguru`, `pydantic`, `sqlite3`（現有相依）
- **輸出格式**：Markdown（Humanize-ZH 標準）、JSON、LINE 友好格式
- **市場支援**：`"tw"`, `"us"`, `"both"`（現有設計）
- **LLM 抽象**：允許外部注入 `LLMClient` 實作
- **測試**：每個任務需包含單元測試，整合測試涵蓋三種場景

---

### Task 1: LLM 抽象介面

**Files:**
- Create: `skills/alphaear-reporter/scripts/utils/llm/base_client.py`
- Create: `skills/alphaear-reporter/scripts/utils/llm/default_client.py`
- Modify: `skills/alphaear-reporter/scripts/utils/llm/router.py:1-50`
- Test: `tests/test_llm_client.py`

**Interfaces:**
- Consumes: 現有 `LLMRouter` 實作
- Produces: `LLMClient` 抽象介面與預設實作

- [ ] **Step 1: 定義抽象介面**
- [ ] **Step 2: 實作預設 LLMClient**
- [ ] **Step 3: 修改現有 LLMRouter 相容性**
- [ ] **Step 4: 撰寫測試**
- [ ] **Step 5: 執行測試並確認失敗**
- [ ] **Step 6: 實作 mock LLMRouter 並通過測試**
- [ ] **Step 7: 重新執行測試**
- [ ] **Step 8: 提交**

---

### Task 2: ReportGenerator 核心邏輯

**Files:**
- Create: `skills/alphaear-reporter/scripts/report_generator.py`
- Test: `tests/test_reporter.py`

**Interfaces:**
- Consumes: `LLMClient`, `DatabaseManager`, 現有 prompt 模組
- Produces: `ReportGenerator.generate_report()` 方法

- [ ] **Step 1: 實作 ReportGenerator 骨架**
- [ ] **Step 2: 實作 `_cluster_signals` 方法**
- [ ] **Step 3: 撰寫測試**
- [ ] **Step 4: 執行測試並確認通過**
- [ ] **Step 5: 實作 `_write_section` 和 `_assemble_report` 方法**
- [ ] **Step 6: 完成 `_simplify_for_line` 方法**
- [ ] **Step 7: 撰寫完整測試**
- [ ] **Step 8: 執行測試並確認通過**
- [ ] **Step 9: 提交**

---

### Task 3: CLI 介面實作

**Files:**
- Create: `skills/alphaear-reporter/scripts/report_cli.py`
- Test: `tests/test_reporter_cli.py`

**Interfaces:**
- Consumes: `ReportGenerator`, `DatabaseManager`
- Produces: CLI 介面（`python -m report_cli`）

- [ ] **Step 1: 實作 CLI 骨架**
- [ ] **Step 2: 撰寫測試**
- [ ] **Step 3: 執行測試並確認通過**
- [ ] **Step 4: 提交**

---

### Task 4: Python API 實作

**Files:**
- Create: `skills/alphaear-reporter/scripts/report_api.py`
- Test: `tests/test_reporter_api.py`

**Interfaces:**
- Consumes: `ReportGenerator`, `DatabaseManager`
- Produces: `ReportAPI` 類別（供 Polaris 後端 import）

- [ ] **Step 1: 實作 Python API**
- [ ] **Step 2: 撰寫測試**
- [ ] **Step 3: 執行測試並確認通過**
- [ ] **Step 4: 提交**

---

### Task 5: Agentic Workflow 相容性修改

**Files:**
- Modify: `skills/alphaear-reporter/scripts/report_agent.py:1-50`
- Test: `tests/test_reporter.py`（現有測試）

**Interfaces:**
- Consumes: `ReportGenerator`
- Produces: 相容現有 Agentic Workflow

- [ ] **Step 1: 修改現有 ReportAgent 使用 ReportGenerator**
- [ ] **Step 2: 更新現有測試**
- [ ] **Step 3: 執行測試並確認通過**
- [ ] **Step 4: 提交**

---

### Task 6: 整合測試與文件更新

**Files:**
- Modify: `skills/alphaear-reporter/SKILL.md`
- Create: `tests/test_integration.py`

**Interfaces:**
- Consumes: 所有實作元件
- Produces: 整合測試與更新文件

- [ ] **Step 1: 撰寫整合測試**
- [ ] **Step 2: 執行整合測試**
- [ ] **Step 3: 更新 SKILL.md 文件**
- [ ] **Step 4: 提交整合測試與文件**