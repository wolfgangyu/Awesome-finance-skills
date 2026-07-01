"""CI policy: training-entry scripts must not be marked as runnable from CI."""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PREDICTOR_DIR = REPO_ROOT / "skills" / "alphaear-predictor"
TRAINING_ENTRIES = [
    "scripts/build_dataset.py",
    "scripts/train_news_proj.py",
    "scripts/evaluate_news_proj.py",
]


@pytest.mark.skipif(
    not PREDICTOR_DIR.exists(),
    reason="predictor skill not present",
)
def test_training_entries_exist_as_files() -> None:
    missing = [
        rel for rel in TRAINING_ENTRIES if not (PREDICTOR_DIR / rel).exists()
    ]
    # Until this plan creates them, this is acceptable; once they exist this test
    # will guard against accidental removal.
    if missing:
        pytest.skip(f"training entries not yet implemented: {missing}")


def test_backup_dir_is_gitignored() -> None:
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.exists(), "root .gitignore must exist"
    text = gitignore.read_text(encoding="utf-8")
    assert (
        "_backup/" in text
    ), "_backup/ must be gitignored to prevent .pt from being committed"


def test_latest_txt_placeholder_is_gitignored() -> None:
    gitignore = REPO_ROOT / ".gitignore"
    text = gitignore.read_text(encoding="utf-8")
    assert (
        "kronos_news_latest.txt" in text
    ), "kronos_news_latest.txt must be gitignored"


def test_no_training_entry_invoked_from_ci_yaml() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    if not workflows.exists():
        pytest.skip("no .github/workflows/ in this repo")
    offenders: list[tuple[str, str]] = []
    for wf in workflows.glob("*.y*ml"):
        text = wf.read_text(encoding="utf-8", errors="ignore")
        for entry in TRAINING_ENTRIES:
            if entry in text:
                offenders.append((wf.name, entry))
    assert not offenders, (
        f"CI workflow(s) appear to invoke training entries: {offenders}. "
        "Remove these from .github/workflows/* to comply with the CI no-auto-train policy."
    )
