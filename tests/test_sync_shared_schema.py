"""sync_shared_schema.py 的契約測試。"""
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SHARED_DIR = REPO / "skills" / "_shared" / "alphaear_schema"
SKILLS = ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]


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


def test_vendor_matches_shared_byte_for_byte():
    """vendor 內的 .py 必須等於 _shared source-of-truth。"""
    _run()  # 確保 vendor 是最新
    for name in ("models.py", "isq_template.py", "__init__.py"):
        src = (SHARED_DIR / name).read_bytes()
        for skill in SKILLS:
            vendor = REPO / "skills" / skill / "scripts" / "alphaear_schema" / name
            assert vendor.exists(), f"{skill}: vendor 缺 {name}"
            assert vendor.read_bytes() == src, (
                f"{skill}: vendor 的 {name} 漂移，必須跑 sync_shared_schema.py"
            )


def test_check_returns_zero_when_all_fresh():
    """所有 vendor 與 shared 一致時，--check 必須 exit 0。"""
    _run()  # 確保 fresh
    chk = _run("--check")
    assert chk.returncode == 0, chk.stdout
    assert "No drift detected" in chk.stdout


def test_check_detects_partial_vendor_missing():
    """當任一 vendor 目錄不存在時，--check 必須 exit 1。"""
    _run()
    target = REPO / "skills" / "alphaear-reporter" / "scripts" / "alphaear_schema"
    backup = target.with_suffix(".bak")
    if backup.exists():
        # 先清乾淨
        import shutil
        shutil.rmtree(backup)
    target.rename(backup)
    try:
        chk = _run("--check")
        assert chk.returncode != 0
        assert "ERROR" in chk.stdout
    finally:
        backup.rename(target)


def test_check_detects_manually_edited_vendor():
    """手動修改任一 vendor 的 .py 後 --check 必須能偵測為 drift。"""
    _run()
    target = REPO / "skills" / "alphaear-signal-tracker" / "scripts" / "alphaear_schema" / "models.py"
    original = target.read_text(encoding="utf-8")
    tampered = original + "\n# tampered\n"
    target.write_text(tampered, encoding="utf-8")
    try:
        chk = _run("--check")
        assert chk.returncode != 0
    finally:
        target.write_text(original, encoding="utf-8")


def test_vendored_version_stamp_matches():
    """__vendored__.py 內 __version__ 必須與 _shared/__init__.py 一致。"""
    _run()
    shared_version = None
    for line in (SHARED_DIR / "__init__.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            shared_version = line.split("=", 1)[1].strip().strip('"\'')
            break
    assert shared_version is not None

    for skill in SKILLS:
        stamp = REPO / "skills" / skill / "scripts" / "alphaear_schema" / "__vendored__.py"
        text = stamp.read_text(encoding="utf-8")
        assert shared_version in text, f"{skill}: __vendored__.py 缺版本 {shared_version}"

