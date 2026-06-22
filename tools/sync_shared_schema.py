#!/usr/bin/env python3
"""sync_shared_schema.py

將 ``skills/_shared/alphaear_schema/`` 單向同步到所有需要 schema 的 skill 之中。
所有 write 都由本腳本掌控，禁止手動修改 vendor 目錄。

用法:
    python tools/sync_shared_schema.py          # 同步所有 skill
    python tools/sync_shared_schema.py --check  # 僅檢查 drift
    python tools/sync_shared_schema.py --help
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED_SRC = REPO_ROOT / "skills" / "_shared" / "alphaear_schema"
SKILLS = ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]


def _read_version(init_path: Path) -> str | None:
    for line in init_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"\'')
    return None


def get_version() -> str:
    return _read_version(SHARED_SRC / "__init__.py") or "0.0.0"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def sync_skill(skill_name: str) -> Path:
    """將 _shared 同步到 ``skills/<skill>/scripts/alphaear_schema/``。"""
    skill_path = REPO_ROOT / "skills" / skill_name
    vendor_dst = skill_path / "scripts" / "alphaear_schema"
    shim_path = skill_path / "scripts" / "schema" / "models.py"

    shutil.copytree(SHARED_SRC, vendor_dst, dirs_exist_ok=True)

    (vendor_dst / "__vendored__.py").write_text(
        f'__version__ = "{get_version()}"\n'
        f'__commit__ = "{_git_commit()}"\n'
        f'__skill__ = "{skill_name}"\n',
        encoding="utf-8",
    )

    shim_path.parent.mkdir(parents=True, exist_ok=True)
    # shim 目錄 (skills/<skill>/scripts/schema/) 是 package，需有 __init__.py 才可讓
    # `from scripts.schema.models import InvestmentSignal` 通過。
    shim_pkg = shim_path.parent
    init_path = shim_pkg / "__init__.py"
    if not init_path.exists():
        init_path.write_text(
            "# DEPRECATED: 請改用 `from scripts.alphaear_schema import ...`。\n",
            encoding="utf-8",
        )

    shim_path.write_text(
        "# DEPRECATED: 請改用 `from scripts.alphaear_schema import InvestmentSignal`。\n"
        "from scripts.alphaear_schema.models import *  # noqa: F401,F403\n",
        encoding="utf-8",
    )

    return vendor_dst


def cmd_check() -> int:
    shared_version = _read_version(SHARED_SRC / "__init__.py")
    if shared_version is None:
        print("ERROR: skills/_shared/alphaear_schema/__init__.py 缺 __version__")
        return 1

    # 三個樣板檔案都要 byte-for-byte 等於 source-of-truth。
    tracked_files = ("models.py", "isq_template.py", "__init__.py")

    for skill in SKILLS:
        vendor = REPO_ROOT / "skills" / skill / "scripts" / "alphaear_schema"
        if not vendor.exists():
            print(f"ERROR: {vendor} 不存在")
            return 1
        for fname in tracked_files:
            shared_bytes = (SHARED_SRC / fname).read_bytes()
            vendor_bytes = (vendor / fname).read_bytes()
            if shared_bytes != vendor_bytes:
                print(f"ERROR: {vendor}/{fname} 已漂移 (需重跑 sync)")
                return 1
        stamp = vendor / "__vendored__.py"
        vendor_version = _read_version(stamp)
        if vendor_version != shared_version:
            print(f"ERROR: {vendor}/__vendored__.py 版本 {vendor_version} != 共用版 {shared_version}")
            return 1
        shim = REPO_ROOT / "skills" / skill / "scripts" / "schema" / "models.py"
        if not shim.exists():
            print(f"ERROR: {shim} 缺 backward-compat shim")
            return 1

    print("No drift detected")
    return 0


def cmd_sync() -> int:
    for skill in SKILLS:
        vendor_dst = sync_skill(skill)
        print(f"  synced → {vendor_dst}")
    print("Sync complete")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--check", action="store_true", help="僅檢查 drift，不做任何寫入")
    args = parser.parse_args(argv)
    if args.check:
        return cmd_check()
    return cmd_sync()


if __name__ == "__main__":
    sys.exit(main())
