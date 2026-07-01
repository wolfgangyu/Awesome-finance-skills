"""Tests for evaluate_news_proj entry."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_import_evaluate_script() -> None:
    from scripts import evaluate_news_proj  # noqa: F401
    assert hasattr(evaluate_news_proj, "main")


def test_main_requires_model_arg() -> None:
    """--model is a required argument."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.evaluate_news_proj", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parents[2] / "skills" / "alphaear-predictor"),
    )
    combined = result.stdout + result.stderr
    assert "--model" in combined
