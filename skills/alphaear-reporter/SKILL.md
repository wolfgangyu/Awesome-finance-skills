---
name: alphaear-reporter
description: Plan, write, and edit professional financial reports for TW/US markets; generate finance chart configurations. Use when condensing finance analysis into a structured output.
---

# AlphaEar Reporter Skill

## Overview

This skill provides a structured workflow for generating professional financial reports focused on **Taiwan (TWSE/TPEx)** and **US (yfinance)** markets. It includes planning, writing, editing, and creating visual aids (charts).

### Shared Schema

本 skill 內含 vendored 版的 `alphaear_schema`（single source of truth 在 `skills/_shared/alphaear_schema/`）。修改 schema 必須在 `_shared/` 內編輯後跑 `python tools/sync_shared_schema.py`。

> 版本戳記: `skills/alphaear-reporter/scripts/alphaear_schema/__vendored__.py`

## Capabilities

### 1. Generate Structured Reports (Agentic Workflow)

**YOU (the Agent)** are the Report Generator. Use the prompts in `scripts/prompts/` to progressively build the report.

**Workflow:**
1.  **Cluster Signals**: Read input signals and use the **Cluster Signals Prompt** to group them.
2.  **Write Sections**: For each cluster, use the **Write Section Prompt** to generate analysis.
3.  **Assemble**: Use the **Final Assembly Prompt** to compile the report.

### 2. Visualization Tools

Use `scripts/visualizer.py` to generate chart configurations if needed manually, though the Writer Prompt usually handles this via `json-chart` blocks.

## Market & Language Settings

### Market Parameter (`market`)

The reporter supports three market modes. These affect:
- Default news sources (CNA for TW, Bloomberg/Reuters for US)
- Ticker format examples in prompts
- Stock data source references (TWSE/TPEx vs yfinance)

| Value | Description | Default News Sources | Ticker Format |
|:-----|:-----|:-----|:-----|
| `"tw"` | Taiwan market (default) | `cna_finance`, `cna_tech` | 4-digit (e.g., `2330.TW`) |
| `"us"` | US market | `bloomberg`, `investing_reuters` | 1-5 letters (e.g., `AAPL`) |
| `"both"` | Both TW + US | `cna_finance`, `bloomberg` | Both formats |

### Language Requirement (Humanize-ZH)

All report output must follow the **Humanize-ZH** writing standards:
- **全程使用繁體中文**（禁止簡體中文字元）
- **中文字與英文/數字之間加半形空格**（如：T+5 預測、AAPL 股價）
- **保留專業術語的英文和縮寫**（如 TWSE、TPEx、ISQ、K 線）
- **語氣自然不生硬**（避免 AI 腔調）
- **數字格式**：金額千分位（NT$ 1,234,567），百分比兩位小數（+3.45%）

## Dependencies

-   `sqlite3` (built-in)
