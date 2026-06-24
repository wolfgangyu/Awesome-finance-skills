"""安全轉換：先判斷編碼，再轉換。"""
import sys
from pathlib import Path
import chardet


def detect_encoding(path: Path) -> str:
    raw = path.read_bytes()
    result = chardet.detect(raw)
    return result["encoding"] or "utf-8"


def convert_file_safely(path: Path) -> bool:
    enc = detect_encoding(path)
    print(f"{path} detected as {enc}")
    text = path.read_text(encoding=enc)

    # 這裡放你的 convert_text 邏輯
    from tools.convert_zh_tw import convert_text
    new_text = convert_text(text)

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"converted: {path}")
        return True
    return False


if __name__ == "__main__":
    for p in sys.argv[1:]:
        convert_file_safely(Path(p))