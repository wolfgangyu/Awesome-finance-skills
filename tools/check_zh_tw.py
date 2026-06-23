"""檢查 repo 內是否有簡體中文殘餘。

用法：
  python tools/check_zh_tw.py <root>

輸出：
  - 每個檔案的簡體片語列表
  - exit 1 表示有殘餘
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from convert_zh_tw import is_simplified, iter_target_files


def main() -> int:
    parser = argparse.ArgumentParser(description="檢查簡體中文殘餘")
    parser.add_argument("paths", nargs="+", type=Path, help="要掃描的根目錄或檔案")
    args = parser.parse_args()

    found = False
    for path in iter_target_files(args.paths):
        text = path.read_text(encoding="utf-8")
        if is_simplified(text):
            print(f"❌ {path}")
            found = True
    if found:
        print("\n❌ Found Simplified Chinese residue.")
        return 1
    print("✅ All files are in Traditional Chinese.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
