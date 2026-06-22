---
name: alphaear-reporter
description: Plan, write, and edit professional financial reports; generate finance chart configurations. Use when condensing finance analysis into a structured output.
---

# AlphaEar Reporter Skill

## Overview

This skill provides a structured workflow for generating professional financial reports. It includes planning, writing, editing, and creating visual aids (charts).

### Shared Schema

本 skill 內含 vendored 版的 `alphaear_schema`（single source of truth 在 `skills/_shared/alphaear_schema/`）。修改 schema 必須在 `_shared/` 內編輯後跑 `python tools/sync_shared_schema.py`。

> 版本戳記: `skills/alphaear-reporter/scripts/alphaear_schema/__vendored__.py`

## Capabilities

## Capabilities

### 1. Generate Structured Reports (Agentic Workflow)

**YOU (the Agent)** are the Report Generator. Use the prompts in `references/PROMPTS.md` to progressively build the report.

**Workflow:**
1.  **Cluster Signals**: Read input signals and use the **Cluster Signals Prompt** to group them.
2.  **Write Sections**: For each cluster, use the **Write Section Prompt** to generate analysis.
3.  **Assemble**: Use the **Final Assembly Prompt** to compile the report.

### 2. Visualization Tools

Use `scripts/visualizer.py` to generate chart configurations if needed manually, though the Writer Prompt usually handles this via `json-chart` blocks.

## Dependencies

-   `sqlite3` (built-in)

