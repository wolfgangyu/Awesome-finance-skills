"""繁中化工具的契約測試。"""
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools.convert_zh_tw import (  # noqa: E402
    is_simplified,
    convert_text,
    mapping,
)  # noqa: E402


def test_converter_maps_known_terms():
    """spec §5.3 詞彙對照必須生效。"""
    pairs = {
        "股票代码": "股票代號",
        "记忆": "記憶體",
        "网络": "網路",
        "重新获取": "重新取得",
        "信号": "訊號",
        "下载": "下載",
        "本地": "本機",
        "软件": "軟體",
        "消息": "訊息",
        "证券": "證券",
        "开盘": "開盤",
        "收盘": "收盤",
        "涨跌幅": "漲跌幅",
        "换手率": "換手率",
        "成交额": "成交額",
        "涨跌额": "漲跌額",
    }
    for src, expected in pairs.items():
        got = convert_text(src)
        assert got == expected, f"{src} → got {got!r}, expected {expected!r}"


def test_is_simplified_detects_known_terms():
    """應能辨識 spec §5.3 中的簡體詞。"""
    assert is_simplified("这段代码有简体的「股票代码」")
    assert is_simplified("网络超时")
    assert is_simplified("本地缓存")
    # 繁中不可被誤識為簡體
    assert not is_simplified("這段程式碼完全繁中")
    assert not is_simplified("台灣加權股價指數")


def test_preserves_english_and_punctuation():
    """English、數字、URL 不能被影響（zh-TW 排版規則下我們維持英文 + 內容原貌）。"""
    assert convert_text("TODO and FIXME in code") == "TODO and FIXME in code"
    assert "2.0" in convert_text("Version 2.0")
    # 簡單的英文行不能改造
    assert convert_text("Just English here.") == "Just English here."


def test_script_files_exist():
    """tools/ 目錄下兩支腳本必須存在。"""
    assert (REPO / "tools" / "convert_zh_tw.py").exists()
    assert (REPO / "tools" / "check_zh_tw.py").exists()


def test_check_zh_tw_finds_residue():
    """check_zh_tw.py 在虛擬 markdown 上要能找出簡體殘餘。"""
    import subprocess
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        md = Path(tmp) / "sample.md"
        md.write_text("# README\n这是简体的「股票代码」与「网络」。\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "check_zh_tw.py"), str(tmp)],
            capture_output=True, text=True,
        )
        assert "股票代码" in result.stdout or "网络" in result.stdout, result.stdout
        assert result.returncode != 0


def test_check_zh_tw_clean_returns_zero():
    """全繁中的 md → exit 0。"""
    import subprocess
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        md = Path(tmp) / "sample.md"
        md.write_text("# 我是繁中的 README\n台灣與國際股市。\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "check_zh_tw.py"), str(tmp)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
