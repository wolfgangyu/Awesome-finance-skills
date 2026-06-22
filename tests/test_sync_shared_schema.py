"""sync_shared_schema.py 的契約測試。"""
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "sync_shared_schema.py"), *args],
        capture_output=True,
        text=True,
    )


def test_sync_script_help():
    """腳本必須存在且對 --help 可執行。"""
    script = REPO / "tools" / "sync_shared_schema.py"
    assert script.exists(), "tools/sync_shared_schema.py 必須存在"
    result = _run("--help")
    assert result.returncode == 0
    assert "--check" in result.stdout


def test_sync_then_check_passes():
    """跑 sync 再走 --check 必須印 'No drift detected' 且 exit 0。"""
    sync = _run()
    assert sync.returncode == 0, sync.stderr or sync.stdout

    chk = _run("--check")
    assert chk.returncode == 0, chk.stdout
    assert "No drift detected" in chk.stdout


def test_sync_idempotent():
    """重複 sync 後 vendor 版本戳記一致。"""
    _run()
    stamp_path = REPO / "skills" / "alphaear-predictor" / "scripts" / "alphaear_schema" / "__vendored__.py"
    first = stamp_path.read_text(encoding="utf-8")
    _run()
    second = stamp_path.read_text(encoding="utf-8")
    assert first == second
