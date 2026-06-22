# AlphaEar Schema Consolidation Design

**Date**: 2026-06-22
**Author**: Wolfgang Yu
**Status**: Draft (awaiting review)

## 1. Context

### Problem

Three skills (`alphaear-predictor`, `alphaear-reporter`, `alphaear-signal-tracker`) each maintain their own copy of Pydantic schemas:

- `InvestmentSignal`, `TransmissionNode`, `KLinePoint`, `ForecastResult`, `ResearchContext`, `ScanContext`, `SignalCluster`, `ClusterContext`, `IntentAnalysis`, `FilterResult`
- These schemas are **95% identical** across skills, leading to:
  - **Maintenance drift**: bug fixes or new fields must be manually synced to three places.
  - **Version skew**: downstream consumers (e.g., DeepEar) may receive different schema versions depending on which skill they install.
  - **Testing overhead**: smoke tests must validate three copies of the same contract.

### Goal

- **Single source of truth**: one canonical schema definition.
- **Zero external dependency**: maintain the ability to install a single skill without requiring additional packages.
- **Backward compatibility**: existing imports continue to work during a deprecation period.
- **Clear migration path**: downstream consumers can migrate to the new import path at their own pace.

## 2. Architecture

### 2.1. Directory Layout

```
Awesome-finance-skills/
├── skills/
│   ├── _shared/
│   │   └── alphaear_schema/          # ← Single source of truth (Python package)
│   │       ├── __init__.py           #   exports all models
│   │       ├── models.py            #   InvestmentSignal, KLinePoint, ...
│   │       ├── isq_template.py      #   DEFAULT_ISQ_TEMPLATE
│   │       └── __vendored__.py      #   version stamp (written by sync script)
│   └── <skill>/
│       ├── scripts/
│       │   └── alphaear_schema/      # ← Vendored copy (managed by sync script)
│       │       ├── __init__.py       #   re-exports from _shared
│       │       ├── models.py
│       │       ├── isq_template.py
│       │       └── __vendored__.py
│       └── SKILL.md
├── tools/
│   └── sync_shared_schema.py       # ← One-way sync: _shared → skills
```

### 2.2. Data Flow

1. **Edit**: Human edits only `skills/_shared/alphaear_schema/`.
2. **Sync**: Run `tools/sync_shared_schema.py` to copy `_shared/alphaear_schema/` to each skill's `scripts/alphaear_schema/`.
3. **Vendor**: Each skill's vendored copy is **read-only**; the sync script is the only process allowed to write it.
4. **Import**: Skills import from their own vendored copy (`from scripts.alphaear_schema import InvestmentSignal`).

### 2.3. Sync Script Contract

```bash
# Sync all skills
python tools/sync_shared_schema.py

# Check for drift (CI/pre-commit)
python tools/sync_shared_schema.py --check
```

- **Atomicity**: If any skill fails to sync, the entire transaction rolls back (no partial updates).
- **Versioning**: Writes `__version__` and commit hash to `__vendored__.py`.
- **Deprecation shim**: Temporarily leaves `scripts/schema/models.py` as a re-export wrapper (see §4).

## 3. Schema Consolidation

### 3.1. Base Schema (alphaear-predictor)

The following models are **fully consolidated** into `alphaear_schema/models.py`:

| Model | Fields | Notes |
|:------|:-------|:------|
| `InvestmentSignal` | `signal_id`, `title`, `summary`, `reasoning`, `transmission_chain`, `sentiment_score`, `confidence`, `intensity`, `expectation_gap`, `timeliness`, `expected_horizon`, `price_in_status`, `impact_tickers`, `industry_tags`, `sources` | Core signal model |
| `TransmissionNode` | `node_name`, `impact_type`, `logic` | Chain node |
| `KLinePoint` | `date`, `open`, `high`, `low`, `close`, `volume` | OHLCV data |
| `ForecastResult` | `ticker`, `base_forecast`, `adjusted_forecast`, `rationale`, `timestamp` | Forecast container |
| `ResearchContext` | `raw_signal`, `tickers_found`, `industry_background`, `latest_developments`, `key_risks`, `search_results_summary` | Research data |
| `ScanContext` | `hot_topics`, `news_summaries`, `market_data`, `sentiment_overview`, `raw_data_summary` | Scan data |
| `SignalCluster` | `theme_title`, `signal_ids`, `rationale` | Cluster metadata |
| `ClusterContext` | `clusters` | Cluster container |
| `IntentAnalysis` | `keywords`, `search_queries`, `is_specific_event`, `time_range`, `intent_summary` | Intent data |
| `FilterResult` | `has_valid_signals`, `selected_ids`, `themes`, `reason` | Filter result |

### 3.2. Skill-Specific Extensions

| Skill | Extension | Handling |
|:------|:----------|:---------|
| `alphaear-predictor` | `Evaluation`, `Training` (in `utils/predictor/`) | **Not consolidated** (predictor-only training infra) |
| `alphaear-reporter` | `InvestmentReport` (extends `InvestmentSignal`) | **Consolidated** into `alphaear_schema/models.py` with `extra="allow"` |
| `alphaear-signal-tracker` | None | Fully consolidated |

### 3.3. Deprecation Handling

- **Backward compatibility**: Fields that are being phased out are marked with `Field(..., deprecated=True)`.
- **Validation**: Pydantic v2 automatically emits `DeprecationWarning` on use.
- **Serialization**: `model_dump(mode="json")` includes deprecated fields by default (configurable).

Example:

```python
from pydantic import Field

class InvestmentSignal(BaseModel):
    old_field: Optional[str] = Field(default=None, deprecated=True)
```

## 4. Deprecation Shim

### 4.1. Purpose

- Allow existing imports (`from scripts.schema.models import InvestmentSignal`) to continue working during the deprecation period.
- Provide a clear migration path to the new import path (`from scripts.alphaear_schema import InvestmentSignal`).

### 4.2. Implementation

In each skill's `scripts/schema/models.py`:

```python
# DEPRECATED: Migrate to `from scripts.alphaear_schema import InvestmentSignal`
from scripts.alphaear_schema.models import *  # noqa: F401,F403
```

### 4.3. Timeline

| Version | Action | Impact |
|:--------|:-------|:-------|
| **v1.1.0** | Add shim | Both import paths work |
| **v1.1.1–v1.1.x** | Maintain shim | Backward compatible |
| **v1.2.0** | Remove shim | `from scripts.schema.models` raises `ImportError` |

## 5. Testing

### 5.1. Schema Consistency

- **Test**: `tests/test_shared_schema.py`
  - Import `from alphaear_schema import InvestmentSignal`.
  - Validate round-trip JSON serialization.
  - Ensure deprecated fields are ignored in `model_dump(exclude_deprecated=True)`.

- **Test**: `tests/test_schema_consistency.py`
  - Assert all vendored copies have the same `__version__`.
  - Assert no manual edits to vendored directories (hash mismatch).

### 5.2. Deprecation Shim

- **Test**: `tests/test_deprecation_shim.py`
  - Import `from scripts.schema.models import InvestmentSignal`.
  - Assert it resolves to the vendored copy.
  - Assert `DeprecationWarning` is emitted on use.

### 5.3. Skill-Specific Tests

- **No changes required**: Existing smoke tests continue to pass (they use the shim).
- **Post-v1.2.0**: Update tests to use the new import path.

## 6. Rollout Plan

### 6.1. Phase 1: Implementation (v1.1.0)

1. Create `skills/_shared/alphaear_schema/` and populate with consolidated schemas.
2. Implement `tools/sync_shared_schema.py`.
3. Run sync script to vendor schemas into all three skills.
4. Add deprecation shim to `scripts/schema/models.py`.
5. Update SKILL.md dependencies to note the vendored schema.
6. Add pre-commit hook for `sync_shared_schema.py --check`.

### 6.2. Phase 2: Maintenance (v1.1.1–v1.1.x)

- All schema changes **must** go through `_shared/alphaear_schema/`.
- Run sync script after every change.
- Monitor downstream consumers for migration progress.

### 6.3. Phase 3: Cleanup (v1.2.0)

1. Remove deprecation shim (`scripts/schema/models.py`).
2. Update all internal imports to use `scripts.alphaear_schema`.
3. Update tests to use the new import path.
4. Update README to reflect the new import path.

## 7. Out of Scope

- **Prompts**: Shared prompt strings (e.g., `references/PROMPTS.md`) are not consolidated in this spec.
- **Toolkits**: Shared utility classes (e.g., `scripts/utils/toolkits.py`) are not consolidated.
- **Training infrastructure**: Predictor-specific training/evaluation code remains in `alphaear-predictor`.
- **Database schemas**: Each skill's `DatabaseManager` remains independent.

## 8. Risks and Mitigations

| Risk | Mitigation |
|:-----|:-----------|
| Vendored copies drift from source | Pre-commit hook enforces sync; CI fails on drift |
| Downstream consumers ignore deprecation | Clear timeline in README; CHANGELOG entry for v1.2.0 |
| Schema changes break downstream | Semantic versioning; deprecation warnings before removal |
| Sync script fails mid-transaction | Atomic writes (tmp dir + rename) |

## 9. Appendix

### 9.1. Example: InvestmentSignal

```python
# skills/_shared/alphaear_schema/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class TransmissionNode(BaseModel):
    node_name: str
    impact_type: str
    logic: str

class InvestmentSignal(BaseModel):
    signal_id: str = "unknown_sig"
    title: str
    summary: str = "暂无摘要分析"
    reasoning: str = ""
    transmission_chain: List[TransmissionNode] = []
    sentiment_score: float = 0.0
    confidence: float = 0.5
    intensity: int = 3
    expectation_gap: float = 0.5
    timeliness: float = 0.8
    expected_horizon: str = "T+N"
    price_in_status: str = "未知"
    impact_tickers: List[Dict] = []
    industry_tags: List[str] = []
    sources: List[Dict] = []
    # Deprecated fields
    old_field: Optional[str] = Field(default=None, deprecated=True)
```

### 9.2. Sync Script Pseudocode

```python
import shutil
from pathlib import Path

def sync_skill(skill_path: Path):
    shared_src = Path("skills/_shared/alphaear_schema")
    vendor_dst = skill_path / "scripts/alphaear_schema"
    shim_path = skill_path / "scripts/schema/models.py"
    
    # Copy shared schema to vendor dir
    shutil.copytree(shared_src, vendor_dst, dirs_exist_ok=True)
    
    # Write version stamp
    with open(vendor_dst / "__vendored__.py", "w") as f:
        f.write(f"__version__ = '{get_version()}'\n")
    
    # Add deprecation shim
    with open(shim_path, "w") as f:
        f.write("# DEPRECATED: Migrate to `scripts.alphaear_schema`\n")
        f.write("from scripts.alphaear_schema.models import *  # noqa\n")
```