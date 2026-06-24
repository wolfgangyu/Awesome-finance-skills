"""檢查 repo 內是否有簡體中文殘餘。

用法：
  python tools/check_zh_tw.py <root>

輸出：
  - 每個檔案的簡體片語列表
  - exit 1 表示有殘餘
  - 如發現 Unicode replacement char (U+FFFD) 表示檔案有雙編碼問題，會另行列出
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from convert_zh_tw import is_simplified, has_encoding_problem, iter_target_files


def main() -> int:
    parser = argparse.ArgumentParser(description="檢查簡體中文殘餘")
    parser.add_argument("paths", nargs="+", type=Path, help="要掃描的根目錄或檔案")
    args = parser.parse_args()

    found = False
    encoding_problems = []
    for path in iter_target_files(args.paths):
        raw = path.read_bytes()
        text = None
        for enc in ("utf-8", "utf-8-sig", "cp950", "gb2312", "gbk"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("utf-8", errors="replace")
        if has_encoding_problem(text):
            encoding_problems.append(path)
        if is_simplified(text):
            print(f"[FOUND] {path}")
            found = True
    if encoding_problems:
        print("\n[WARN] 下列檔案含有雙編碼或 Unicode replacement char，請手動 review：")
        for p in encoding_problems:
            print(f"  - {p}")
    if found:
        print("\n[FAIL] Simplified Chinese residue detected.")
        return 1
    print("[OK] All files are in Traditional Chinese.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
