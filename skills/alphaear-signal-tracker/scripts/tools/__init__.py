# src/tools/__init__.py
"""
AlphaEar 工具套件层 - Agno Toolkit 适配器

提供的 Toolkit 類別：
- NewsToolkit: 热点新闻取得
- StockToolkit: 股票搜尋与价格查询
- SentimentToolkit: 情绪分析
- SearchToolkit: 網路搜尋
"""

from .toolkits import (
    NewsToolkit,
    StockToolkit,
    SentimentToolkit,
    SearchToolkit,
)

__all__ = [
    "NewsToolkit",
    "StockToolkit",
    "SentimentToolkit",
    "SearchToolkit",
]
