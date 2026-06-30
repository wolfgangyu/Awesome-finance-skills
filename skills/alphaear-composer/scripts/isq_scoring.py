"""ISQ Scoring — 投資訊號評分模組。

提供兩種模式：
1. Heuristic（預設）：從新聞數量、sentiment、價格波動自動計算
2. LLM（高品質）：調用 LLM 產出更精確的評分

ISQ 維度：
- sentiment_score: -1.0 ~ +1.0  （新聞情緒）
- confidence: 0.0 ~ 1.0         （信心指數）
- intensity: 1 ~ 5              （影響強度）
- expectation_gap: 0.0 ~ 1.0    （預期落差）
- timeliness: 0.0 ~ 1.0         （時效性）

Composite score: confidence*0.35 + (intensity/5)*0.30 + expectation_gap*0.20 + timeliness*0.15
"""

import math
from typing import Dict, Any, List, Optional
from loguru import logger


def heuristic_score(
    news_items: List[Dict[str, Any]],
    price_changes: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Heuristic ISQ 評分 — 不需要 LLM。

    從新聞和股價資料自動計算 ISQ 分數。

    Args:
        news_items: 新聞列表（含 sentiment_score 欄位）
        price_changes: 價格變動百分比列表（可選）

    Returns:
        {
            "sentiment_score": float,
            "confidence": float,
            "intensity": int,
            "expectation_gap": float,
            "timeliness": float,
        }
    """
    # --- sentiment_score: 新聞情緒平均 ---
    sentiments = [n.get("sentiment_score", 0.0) for n in news_items if n.get("sentiment_score") is not None]
    if sentiments:
        avg_sentiment = sum(sentiments) / len(sentiments)
    else:
        avg_sentiment = 0.0
    # 如果沒有 sentiment 資料但有新聞，給一個中性偏正面的預設值
    if not sentiments and news_items:
        avg_sentiment = 0.1

    # --- confidence: 新聞數量 + 一致性 ---
    news_count = len(news_items)
    # 新聞越多 confidence 越高，但遞減
    confidence_from_volume = min(1.0, 0.3 + 0.1 * math.log1p(news_count))
    # 如果有多篇新聞且 sentiment 一致，再加權
    if len(sentiments) >= 2:
        variance = sum((s - avg_sentiment) ** 2 for s in sentiments) / len(sentiments)
        consistency_bonus = max(0, 0.2 - 0.1 * variance)
        confidence = min(1.0, confidence_from_volume + consistency_bonus)
    else:
        confidence = confidence_from_volume

    # --- intensity: 基於新聞數量和價格波動 ---
    intensity = 1  # 基礎值
    if news_count >= 5:
        intensity = 5
    elif news_count >= 3:
        intensity = 4
    elif news_count >= 2:
        intensity = 3
    else:
        intensity = 2

    # 如果有價格波動資料，放大 intensity
    if price_changes:
        avg_abs_change = sum(abs(c) for c in price_changes) / len(price_changes)
        if avg_abs_change > 5.0:
            intensity = min(5, intensity + 1)
        elif avg_abs_change > 3.0:
            intensity = min(5, intensity + 1)

    # --- expectation_gap: 價格波動越大，落差越大 ---
    if price_changes:
        max_change = max(abs(c) for c in price_changes)
        expectation_gap = min(1.0, max_change / 20.0)  # 20% 波動 = 滿分
    else:
        # 沒有價格資料，用新聞數量推估
        expectation_gap = min(1.0, news_count * 0.15)

    # --- timeliness: 越新的新聞時效性越高 ---
    # 預設為 0.7（假設是近期的新聞）
    timeliness = 0.7
    if price_changes and len(price_changes) > 0:
        # 有近期價格波動，時效性更高
        timeliness = min(1.0, 0.7 + 0.1 * min(len(price_changes), 5))

    return {
        "sentiment_score": round(avg_sentiment, 2),
        "confidence": round(confidence, 2),
        "intensity": intensity,
        "expectation_gap": round(expectation_gap, 2),
        "timeliness": round(timeliness, 2),
    }


def composite_score(isq: Dict[str, Any]) -> float:
    """計算 ISQ 綜合分數。

    Formula: confidence*0.35 + (intensity/5)*0.30 + expectation_gap*0.20 + timeliness*0.15
    """
    return round(
        isq["confidence"] * 0.35
        + (isq["intensity"] / 5) * 0.30
        + isq["expectation_gap"] * 0.20
        + isq["timeliness"] * 0.15,
        2,
    )
