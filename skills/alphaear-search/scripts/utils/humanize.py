"""繁體中文人性化格式化工具。

優先使用 lab-drawer 的 humanizer 模組，若無法載入則使用內建格式化。
"""

from datetime import datetime, timezone, timedelta
from loguru import logger

_HUMANIZER_AVAILABLE = False
try:
    from humanizer import zh_humanizer  # noqa: F401
    _HUMANIZER_AVAILABLE = True
    logger.info("✅ humanizer loaded from lab-drawer")
except ImportError:
    logger.warning("⚠️ humanizer not available, using built-in formatters")


def humanize_time(dt_str: str) -> str:
    """將 ISO 時間字串轉換為繁體中文自然語言。

    Args:
        dt_str: ISO 格式時間字串，如 '2024-01-15T10:30:00'

    Returns:
        人性化時間字串，如 '3 小時前'、'昨天'、'3 天前'
    """
    if not dt_str:
        return "未知"

    if _HUMANIZER_AVAILABLE:
        try:
            return zh_humanizer.humanize_time(dt_str)
        except Exception:
            pass

    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return dt_str

    now = datetime.now().astimezone()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if now.tzinfo and dt.tzinfo:
        diff = now - dt.astimezone(now.tzinfo)
    else:
        diff = now - dt

    if diff < timedelta(minutes=1):
        return "剛剛"
    elif diff < timedelta(hours=1):
        mins = int(diff.total_seconds() / 60)
        return f"{mins} 分鐘前"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} 小時前"
    elif diff < timedelta(days=7):
        return f"{diff.days} 天前"
    elif diff < timedelta(days=30):
        return f"{diff.days // 7} 週前"
    else:
        return dt.strftime("%Y-%m-%d")


def humanize_number(n: float, decimals: int = 1) -> str:
    """將數字轉換為繁體中文可讀格式。

    Args:
        n: 要格式化的數字
        decimals: 小數位數，預設 1 位

    Returns:
        人性化數字字串，如 '123.5 萬'、'1.2 億'
    """
    if _HUMANIZER_AVAILABLE:
        try:
            return zh_humanizer.humanize_number(n, decimals)
        except Exception:
            pass

    if n < 0:
        return f"-{humanize_number(abs(n), decimals)}"
    if n < 1000:
        return str(int(n)) if decimals == 0 else f"{n:.{decimals}f}"
    elif n < 10000:
        return f"{n / 1000:.{decimals}f} 千"
    elif n < 100000000:
        return f"{n / 10000:.{decimals}f} 萬"
    else:
        return f"{n / 100000000:.{decimals}f} 億"


def humanize_price(price: float, currency: str = "USD") -> str:
    """將價格轉換為繁體中文可讀格式。

    Args:
        price: 價格數值
        currency: 貨幣代碼，預設 'USD'

    Returns:
        人性化價格字串，如 '$150.5'、'NT$500.0'
    """
    if _HUMANIZER_AVAILABLE:
        try:
            return zh_humanizer.humanize_price(price, currency)
        except Exception:
            pass

    currency_map = {
        "USD": "$", "TWD": "NT$", "CNY": "¥",
        "JPY": "¥", "EUR": "€",
    }
    symbol = currency_map.get(currency, currency)

    if abs(price) >= 1000:
        return f"{symbol}{price:,.2f}"
    else:
        return f"{symbol}{price:.2f}"
