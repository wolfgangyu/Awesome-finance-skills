"""Signal Formation — 從原始資料形成 InvestmentSignal。

支援兩種模式：
1. Heuristic：從新聞+股價自動組合 signal（不需 LLM）
2. LLM：調用 LLM 產生更精確的分析（需要 LLM API）
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger

from isq_scoring import heuristic_score, composite_score


def _generate_signal_id(title: str, news_ids: List[str]) -> str:
    """產生唯一的 signal_id。"""
    raw = f"{title}|{','.join(news_ids)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _detect_ticker(text: str) -> Optional[str]:
    """從文字中偵測股票代碼。"""
    # 台股：4 位數字
    tw_match = re.search(r'\b(\d{4})\b', text)
    if tw_match:
        return tw_match.group(1)
    # 美股：字母代碼
    us_match = re.search(r'\b([A-Z]{1,5})\b', text)
    if us_match:
        candidate = us_match.group(1)
        # 排除常見非 ticker 單字
        stopwords = {"THE", "AND", "FOR", "NOT", "NEW", "NOW", "MKT", "USA", "ONE", "TWO", "THREE", "HIGH", "LOW", "OPEN", "CLOSE", "PRICE", "DATA", "NEWS", "INFO", "READ", "SEARCH", "GET", "TOP", "KEY", "SET", "USE", "RUN", "BIG", "ALL", "CAN", "HAS", "HOW", "WHO", "WHY", "WAS", "DAY", "GET", "MAY", "SAY", "SHE", "TOO"}
        if candidate not in stopwords:
            return candidate
    return None


def _extract_tickers_from_news(news_items: List[Dict[str, Any]]) -> List[str]:
    """從新聞集合中提取 ticker。"""
    tickers = set()
    combined_text = " ".join(n.get("title", "") + " " + n.get("content", "") for n in news_items)
    t = _detect_ticker(combined_text)
    if t:
        tickers.add(t)
    return list(tickers)


def _build_transmission_chain(news_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """根據新聞內容自動建構傳導鏈。"""
    chain = []

    # 簡單規則：如果新聞提到產業關鍵字，加入對應鏈節點
    keywords_to_nodes = {
        "AI": "人工智慧",
        "半導體": "半導體製造",
        "storage": "儲存設備",
        "DRAM": "記憶體",
        "NAND": "閃存",
        "HBM": "高頻寬記憶體",
        "台積電": "晶圓代工",
        "台积电": "晶圓代工",
        "鴻海": "電子代工",
        "富士康": "電子代工",
        "聯發科": "IC設計",
        "MTK": "IC設計",
        "權仁德": "IC設計",
        "光罩": "半導體材料",
        "材料": "原物料",
        "需求": "終端需求",
        "供應鏈": "供應鏈",
        "營收": "財務表現",
        "財報": "財務表現",
    }

    found_nodes = set()
    for news in news_items:
        text = (news.get("title", "") + " " + news.get("content", "")).lower()
        for kw, node_name in keywords_to_nodes.items():
            if kw.lower() in text and node_name not in found_nodes:
                found_nodes.add(node_name)
                chain.append({
                    "node_name": node_name,
                    "impact_type": "利好" if "漲" in text or "升" in text or "growth" in text else "中性",
                    "logic": f"新聞提及 {kw} 相關議題",
                })

    # 如果沒有找到產業關鍵字，至少加一個基礎節點
    if not chain:
        chain.append({
            "node_name": "市場資訊",
            "impact_type": "中性",
            "logic": "基於新聞聚合分析",
        })

    return chain[:5]  # 最多 5 個節點


def _build_summary(news_items: List[Dict[str, Any]], sentiment: float) -> str:
    """從新聞產生摘要。"""
    if not news_items:
        return "無足夠資料產生訊號。"

    # 取最新新聞的標題
    titles = [n.get("title", "") for n in news_items[:3] if n.get("title")]
    if titles:
        base = "、".join(titles[:2])
    else:
        base = f"{len(news_items)} 則相關新聞"

    # 附加情緒方向
    if sentiment > 0.2:
        direction = "整體情緒偏正面"
    elif sentiment < -0.2:
        direction = "整體情緒偏負面"
    else:
        direction = "整體情緒中性"

    return f"{base}。{direction}。"


def form_heuristic_signal(
    news_items: List[Dict[str, Any]],
    price_changes: Optional[List[float]] = None,
    market: str = "both",
) -> Optional[Dict[str, Any]]:
    """Heuristic 模式：從原始資料自動形成 InvestmentSignal。

    Args:
        news_items: 新聞列表
        price_changes: 價格變動列表（可選）
        market: 市場類型 ("tw", "us", "both")

    Returns:
        InvestmentSignal dict，無法形成訊號回傳 None
    """
    if not news_items:
        return None

    # 1. 計算 ISQ
    isq = heuristic_score(news_items, price_changes)

    # 2. 提取 ticker
    tickers = _extract_tickers_from_news(news_items)
    signal_id = tickers[0] if tickers else _generate_signal_id(
        news_items[0].get("title", ""),
        [n.get("id", "") for n in news_items[:3]],
    )

    # 3. 產生摘要
    summary = _build_summary(news_items, isq["sentiment_score"])

    # 4. 建構傳導鏈
    transmission_chain = _build_transmission_chain(news_items)

    # 5. 組合 sources
    sources = []
    for n in news_items[:5]:
        url = n.get("url", "")
        title = n.get("title", "")
        source = n.get("source", n.get("source_name", "unknown"))
        if url:
            sources.append({"title": title, "url": url, "source_name": source})

    # 6. 偵測產業標籤
    industry_tags = set()
    combined = " ".join(n.get("title", "") + " " + n.get("content", "") for n in news_items)
    for tag in ["半導體", "AI", "儲能", "電動車", "晶片", "封測", "記憶體", "光罩", "5G", "雲端", "網際網路"]:
        if tag in combined:
            industry_tags.add(tag)

    # 7. 建構 signal
    signal = {
        "signal_id": signal_id,
        "title": news_items[0].get("title", "")[:30],
        "summary": summary,
        "reasoning": f"基於 {len(news_items)} 則新聞聚合分析。"
                     f"情緒指標: {isq['sentiment_score']:+.2f}，"
                     f"信心指數: {isq['confidence']:.2f}，"
                     f"影響強度: {isq['intensity']}/5。",
        "transmission_chain": transmission_chain,
        "sentiment_score": isq["sentiment_score"],
        "confidence": isq["confidence"],
        "intensity": isq["intensity"],
        "expectation_gap": isq["expectation_gap"],
        "timeliness": isq["timeliness"],
        "expected_horizon": "T+3" if isq["intensity"] >= 4 else "T+1",
        "price_in_status": "未知",
        "impact_tickers": [{"ticker": t, "weight": 1.0} for t in tickers],
        "industry_tags": list(industry_tags),
        "sources": sources,
        "search_results": [],
    }

    # 市場過濾
    if market == "tw" and not any(t.isdigit() for t in tickers):
        return None
    if market == "us" and not any(not t.isdigit() for t in tickers):
        return None

    return signal


def form_signals_from_news(
    news_items: List[Dict[str, Any]],
    price_changes: Optional[List[float]] = None,
    market: str = "both",
) -> List[Dict[str, Any]]:
    """從一批新聞形成多個 signal（按主題分組）。

    目前採用簡單策略：每組新聞產生一個 signal。
    未來可改進為按 ticker/主題自動分群。
    """
    if not news_items:
        return []

    # 簡單分群：按 ticker 分組
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for news in news_items:
        ticker = _detect_ticker(news.get("title", "") + " " + news.get("content", ""))
        if ticker:
            groups.setdefault(ticker, []).append(news)
        else:
            groups.setdefault("_general", []).append(news)

    signals = []
    for group_key, items in groups.items():
        signal = form_heuristic_signal(items, price_changes, market)
        if signal:
            signal["signal_id"] = group_key if group_key != "_general" else signal["signal_id"]
            signals.append(signal)

    # 如果沒分到群，就全部當一個 signal
    if not signals and news_items:
        signal = form_heuristic_signal(news_items, price_changes, market)
        if signal:
            signals.append(signal)

    return signals
