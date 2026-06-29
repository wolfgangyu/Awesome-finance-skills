"""市場感知 prompt 共用工具 — 台美股市化 + 繁體中文規範。

任何需要市場上下文或繁體中文寫作規範的 prompt generator，
都應匯入此模組的常數與 helper。
"""

from __future__ import annotations

from typing import Dict, Literal

MarketType = Literal["tw", "us", "both"]

# ---------------------------------------------------------------------------
# 市場範例資料
# ---------------------------------------------------------------------------

MARKET_EXAMPLES: Dict[MarketType, Dict[str, object]] = {
    "tw": {
        "tickers": [
            {"name": "台積電", "ticker": "2330.TW"},
            {"name": "鴻海", "ticker": "2317.TW"},
            {"name": "聯發科", "ticker": "2454.TW"},
        ],
        "ticker_format": "台股 4 位數字（如 2330）或加 .TW 後綴",
        "ticker_suffix_note": "允許帶 .TW 後綴（如 2330.TW）",
        "news_sources": ["cna_finance", "cna_tech"],
        "isq_example": "建議關注：台積電（2330.TW）...",
        "forecast_example": {"ticker": "2330.TW", "title": "台積電（2330）T+5 預測", "pred_len": 5},
        "transmission_event": "台積電法說會營收創新高",
        "sentiment_keywords": ["台股", "半導體", "台積電"],
        "price_hint": "台股以新台幣計價",
    },
    "us": {
        "tickers": [
            {"name": "Apple", "ticker": "AAPL"},
            {"name": "NVIDIA", "ticker": "NVDA"},
            {"name": "Microsoft", "ticker": "MSFT"},
        ],
        "ticker_format": "美股 1-5 個英文字母（如 AAPL、NVDA）",
        "ticker_suffix_note": "美股代號通常不帶交易所後綴",
        "news_sources": ["bloomberg", "investing_reuters"],
        "isq_example": "建議關注：NVIDIA（NVDA）...",
        "forecast_example": {"ticker": "NVDA", "title": "NVIDIA（NVDA）T+5 預測", "pred_len": 5},
        "transmission_event": "英偉達發布新一代 GPU 架構",
        "sentiment_keywords": ["美股", "科技股", "NVIDIA"],
        "price_hint": "美股以美元計價",
    },
    "both": {
        "tickers": [
            {"name": "台積電", "ticker": "2330.TW"},
            {"name": "Apple", "ticker": "AAPL"},
        ],
        "ticker_format": "台股 4 位數字（如 2330）或美股 1-5 字母（如 AAPL）",
        "ticker_suffix_note": "台股建議加 .TW，美股不加",
        "news_sources": ["cna_finance", "bloomberg"],
        "isq_example": "建議關注：台積電（2330.TW）、NVIDIA（NVDA）...",
        "forecast_example": {"ticker": "2330.TW", "title": "台積電（2330）T+5 預測", "pred_len": 5},
        "transmission_event": "台積電法說會與英偉達 GPU 新品",
        "sentiment_keywords": ["台股", "美股", "半導體"],
        "price_hint": "台股新台幣、美股美元",
    },
}


def get_market_config(market: MarketType) -> Dict[str, object]:
    """回傳指定市場的完整範例 dict。"""
    return MARKET_EXAMPLES[market]


# ---------------------------------------------------------------------------
# 新聞來源預設值
# ---------------------------------------------------------------------------

DEFAULT_SOURCES_BY_MARKET: Dict[MarketType, list[str]] = {
    "tw": ["cna_finance", "cna_tech"],
    "us": ["bloomberg", "investing_reuters"],
    "both": ["cna_finance", "bloomberg"],
}


def get_default_news_sources(market: MarketType) -> list[str]:
    """回傳指定市場的預設新聞來源 ID 列表。"""
    return DEFAULT_SOURCES_BY_MARKET[market]


# ---------------------------------------------------------------------------
# 繁體中文 Humanize 指令（嵌入所有 prompt 結尾）
# ---------------------------------------------------------------------------

HUMANIZE_ZH_INSTRUCTION: str = (
    "### 【重要】語言與格式規範\n"
    "\n"
    "- **全程使用繁體中文**（禁止出現簡體中文字元，如：资料→資料、取得→取得、简化→簡化）。\n"
    "- **中文字與英文/數字之間加半形空格**（如：3 台 iPhone、T+5 預測、AAPL 股價、NT$ 1,000）。\n"
    "- **保留專業術語的英文和縮寫**（如 TWSE、TPEx、yfinance、ISQ、K 線、OHLC、Alpha、Price-in）。\n"
    "- **語氣自然不生硬**，避免 AI 腔調（不要出現「作為一個大型語言模型」、「總結來說」等套話）。\n"
    "- **數字格式**：金額使用千分位（如 NT$ 1,234,567、USD 1,500），百分比保留小數點後兩位（如 +3.45%）。\n"
    "- **排版規則**：中文與英文/數字之間必須有空格，例如「台積電（2330.TW）股價上漲 5%」。\n"
)
