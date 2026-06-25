"""簡體中文 → 繁體中文（台灣）轉換工具。

設計原則：
  1. 只針對 markdown、docstring、log/print/error 等**人類可讀**字串。
  2. 程式碼識別（identifier、URL、檔名、import 名）絕對不能動。
  3. 用 dict-of-str 對照表 + regex。
  4. 標點符號的中英之間保留半形空白（依 CLAUDE.md 全域排版規則）。

詞彙對照表依據 `docs/superpowers/specs/2026-06-22-alphaear-schema-market-refactor-design.md` §5.3。
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

# === 詞彙對照（spec §5.3）===
# 注意：順序敏感（長的在前，避免短詞覆蓋）。
# NOOP_TOKENS 內的「詞」會被 is_simplified 忽略：它們是市場名稱，不算真正
# 需要替換的「簡體」。但仍出現於 README 等敘述裡（如「A股/港股/美股」），
# 不該被樣板替换。
NOOP_TOKENS = {"A股", "港股"}

mapping: list[tuple[str, str]] = [
    # 金融／交易術語
    ("股票代码", "股票代號"),
    ("代码", "代號"),
    # ("股票", "股市"),  # 移除：單字「股票」不該替換，只替換複合詞
    ("重新获取", "重新取得"),
    ("信号", "訊號"),
    ("证券", "證券"),
    ("涨跌幅", "漲跌幅"),
    ("涨幅", "漲幅"),
    ("跌幅", "跌幅"),  # 已是繁中，無須替換
    ("涨跌额", "漲跌額"),
    ("换手率", "換手率"),
    ("成交额", "成交額"),
    ("成交量", "成交量"),  # 已是繁中
    ("开盘", "開盤"),
    ("收盘", "收盤"),
    ("振幅", "振幅"),  # 已是繁中
    ("市场", "市場"),
    ("行业", "行業"),
    ("总市值", "總市值"),
    ("市盈率", "本益比"),
    ("技术", "技術"),
    ("获取", "取得"),
    ("请求", "請求"),
    ("交易", "交易"),  # 已是繁中
    ("失败", "失敗"),
    ("成功", "成功"),  # 已是繁中
    ("加载", "載入"),
    ("下载", "下載"),
    ("上传", "上傳"),
    ("调用", "呼叫"),
    ("响应", "回應"),
    ("支持", "支援"),
    ("默认", "預設"),
    ("更新", "更新"),  # 已是繁中
    ("简介", "簡介"),
    ("描述", "描述"),  # 已是繁中
    ("搜索", "搜尋"),
    ("标签", "標籤"),
    ("列表", "列表"),  # 已是繁中
    ("用户", "使用者"),
    ("插件", "外掛"),
    ("参数", "參數"),
    ("后台", "後台"),
    ("异常", "例外"),
    ("错误", "錯誤"),
    ("警告", "警告"),  # 已是繁中
    ("注释", "註解"),
    ("返回", "回傳"),

    # 網路 / 系統
    ("记忆", "記憶體"),
    ("缓存", "快取"),
    ("网络", "網路"),
    ("本地", "本機"),
    ("软件", "軟體"),
    ("硬件", "硬體"),
    ("消息", "訊息"),
    ("频带宽", "頻寬"),
    ("频道", "頻道"),
    ("频率", "頻率"),

    # 文件/排版
    ("类", "類別"),
    ("对象", "物件"),
    ("数组", "陣列"),
    ("字符", "字元"),
    ("字符串", "字串"),
    ("指针", "指標"),
    ("函数", "函式"),
    ("方法", "方法"),  # 已是繁中
    ("变量", "變數"),
    ("常量", "常數"),
    ("循环", "迴圈"),
    ("模块", "模組"),
    ("包", "套件"),
    ("导出", "匯出"),
    ("导入", "匯入"),
    ("异步", "非同步"),
    ("并发", "並行"),
    ("线程", "執行緒"),
    ("进程", "處理程序"),

    # 動作
    ("设置", "設定"),
    ("删除", "刪除"),
    ("查找", "尋找"),
    ("注意", "注意"),  # 已是繁中
    ("语言", "語言"),
    ("时间", "時間"),
    ("认证", "認證"),
    ("授权", "授權"),
    ("密码", "密碼"),
    ("实时", "即時"),
    ("强化", "強化"),
    ("弱化", "弱化"),  # 已是繁中
    ("证伪", "證偽"),
    ("聚合", "聚合"),
    ("自动", "自動"),
    ("生成", "生成"),
    ("直观", "直觀"),
    ("影响", "影響"),
    ("权重", "權重"),
    ("结合", "結合"),
    ("动态", "動態"),
    ("调整", "調整"),
    ("追踪", "追蹤"),
    ("解读", "解讀"),
    ("综合", "綜合"),
    ("内置", "內建"),
    ("历史", "歷史"),
    ("数据", "資料"),
    ("模型", "模型"),
    ("项目", "專案"),
    ("个人", "個人"),
    ("使用", "使用"),
    ("输入", "輸入"),
    ("输出", "輸出"),
    ("选择", "選擇"),
    ("开始", "開始"),
    ("检查", "檢查"),
    ("风险", "風險"),
    ("分析", "分析"),
    ("财经", "財經"),
    ("个股", "個股"),
    ("评分", "評分"),
    ("分钟", "分鐘"),
    ("基础", "基礎"),
    ("将", "將"),
    ("为", "為"),
    ("时", "時"),
    ("文件", "檔案"),
    ("文件夹", "資料夾"),
    ("开源", "開源"),
    ("首选", "首選"),
    ("分钟级", "分鐘級"),
    ("分钟时间", "分鐘時間"),
]

# 編譯為 regex（一次比對）。只納入 src != dst 的條目。
_PATTERN = re.compile("|".join(re.escape(src) for src, _ in mapping if src != _))


def _longest_first() -> list[tuple[str, str]]:
    """回傳按長度由長到短的對照，保留原 mapping 的次序細節。"""
    return sorted(mapping, key=lambda kv: -len(kv[0]))


_LONGEST_FIRST = _longest_first()


def is_simplified(text: str) -> bool:
    """判斷是否含有**已知**的簡體詞（spec §5.3）。

    不做完整 OpenCC 級別的判斷；只檢查常見的簡體詞是否出現。
    「A股」「港股」是市場名稱，雖然常以簡體寫法保留，但不算真正需要替換的「簡體」
    —— 一律忽略。

    只要 src == dst 的條目一律視為「已知繁中」，不該誤判為簡體。
    """
    if "�" in text:
        return False  # 不擅自處理雙編碼，請人 review
    for src, dst in mapping:
        if src == dst:
            continue
        if src in NOOP_TOKENS:
            continue
        if src in text:
            return True
    return False


def has_encoding_problem(text: str) -> bool:
    """若 text 內含有 replacement char (U+FFFD) 表示這份檔案有雙編碼問題。"""
    return "�" in text


def read_text_safely(path: Path) -> str:
    """讀檔，容忍雙編碼來源（cp950 / GB2312 / UTF-8）。

    git 預設追蹤 UTF-8，但部份維護者歷史留下 cp950 結檔，這裡在寫回時統一為 UTF-8
    以避免跨平台 loss。
    """
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp950", "gb2312", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    # 全部失敗，用 utf-8 + replace 以避免 ValueError
    return raw.decode("utf-8", errors="replace")


def convert_text(text: str) -> str:
    """把一段字串中的簡體片語轉為繁中。

    不變更非中文、英語、數字、標點。
    """
    if not is_simplified(text):
        return text
    # 必須 longest first 才不會被短的先吃
    pattern = re.compile("|".join(re.escape(src) for src, _ in _LONGEST_FIRST))
    lookup = dict(_LONGEST_FIRST)
    return pattern.sub(lambda m: lookup[m.group(0)], text)


def _should_skip_file(path: Path) -> bool:
    """決定一個檔案是否該被略過（binary、build、git 目錄等）。"""
    parts = path.parts
    if any(p in (".git", "venv", "__pycache__", "node_modules", "dist", "build") for p in parts):
        return True
    if path.suffix in (".pyc", ".so", ".dll", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".pt"):
        return True
    return False


def iter_target_files(roots: Iterable[Path], *, include_py: bool = False) -> Iterable[Path]:
    """回傳需要轉換的檔案。

    為避免誤改程式碼（identifier、字串字面值），這個工具**只處理 .md**，
    除非使用者明確加 ``--include-py`` 旗標才擴張到程式碼 docstring。
    """
    suffixes = (".md",) if not include_py else (".md", ".py")
    for root in roots:
        if root.is_file():
            if root.suffix in suffixes:
                yield root
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if _should_skip_file(p):
                continue
            if p.suffix in suffixes:
                yield p


def convert_file(path: Path) -> bool:
    """轉換單一檔案並存回。回傳 True 表示有修改。"""
    text = path.read_text(encoding="utf-8")
    new_text = convert_text(text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="簡轉繁（zh-TW）")
    parser.add_argument("paths", nargs="+", type=Path, help="要掃描的根目錄或檔案")
    parser.add_argument("--dry-run", action="store_true", help="僅列出會動的檔案，不修改")
    parser.add_argument("--include-py", action="store_true", help="包含 .py 檔案（docstrings/log/error 訊息）")
    args = parser.parse_args()

    modified = 0
    fixed_encoding = 0
    for path in iter_target_files(args.paths, include_py=args.include_py):
        raw = path.read_bytes()
        # 先以 UTF-8 試讀；若失敗再嘗試 cp950 → gb2312
        original = None
        text = None
        for enc in ("utf-8", "utf-8-sig", "cp950", "gb2312", "gbk"):
            try:
                text = raw.decode(enc)
                if enc != "utf-8":
                    fixed_encoding += 1
                    print(f"[enc-fix {enc}] {path}")
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("utf-8", errors="replace")
        new_text = convert_text(text)
        if new_text != text:
            modified += 1
            if args.dry_run:
                print(f"would convert: {path}")
            else:
                path.write_text(new_text, encoding="utf-8")
                print(f"converted:     {path}")
    print(f"\nTotal modifications: {modified} (encoding fix: {fixed_encoding})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
