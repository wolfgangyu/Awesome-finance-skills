"""Pytest fixtures for alphaear-predictor TW/US fine-tune tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure predictor skill dir is on sys.path so `scripts.*` imports work.
_PREDICTOR_SKILL = Path(__file__).resolve().parents[2] / "skills" / "alphaear-predictor"
if str(_PREDICTOR_SKILL) not in sys.path:
    sys.path.insert(0, str(_PREDICTOR_SKILL))


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Force every test to use a fresh tmp dir for data caches and parquet outputs."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return data_dir


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-heavy", action="store_true", default=False,
        help="run heavy network/model tests",
    )
    parser.addoption(
        "--ci", action="store_true", default=False,
        help="assert CI policy compliance",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "heavy: network/model-dependent test, skipped by default",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip @heavy tests by default unless --run-heavy is passed."""
    if not config.getoption("--run-heavy", default=False):
        skip_heavy = pytest.mark.skip(
            reason="heavy test (pass --run-heavy to enable)",
        )
        for item in items:
            if "heavy" in item.keywords:
                item.add_marker(skip_heavy)
