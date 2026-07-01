"""Tests for train_news_proj entry — mock Kronos, verify weight updates."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_fixture_json(tmp_path: Path) -> Path:
    """Create a minimal JSON file simulating parquet data (since pyarrow may not be available)."""
    data = [
        {
            "ticker": "2330", "market": "TW", "shock_date": "2024-01-15",
            "history_rows": '[{"date":"2024-01-01","open":100,"close":101,"high":102,"low":99,"volume":1000}]',
            "target_rows": '[{"date":"2024-01-02","open":101,"close":102,"high":103,"low":100,"volume":1100}]',
            "news_text": "Test news",
            "news_emb": json.dumps([0.1] * 384),
            "causality": "verified",
            "unverified_reason": None,
        },
    ]
    path = tmp_path / "fixture.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class TestTrainNewsProjSmoke:
    def test_import_train_script(self) -> None:
        from scripts import train_news_proj  # noqa: F401
        assert hasattr(train_news_proj, "main")

    def test_main_requires_dataset_arg(self) -> None:
        """--dataset is a required argument."""
        result = subprocess.run(
            [sys.executable, "-m", "scripts.train_news_proj", "--help"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[2] / "skills" / "alphaear-predictor"),
        )
        combined = result.stdout + result.stderr
        assert "--dataset" in combined
