"""Serializer — 將 InvestmentReport 序列化為 DeepEar Lite 相容的 latest.json 格式。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger


def _serialize_signal(sig: Dict[str, Any]) -> Dict[str, Any]:
    """將單一 InvestmentSignal dict 轉為 latest.json signal 格式。"""
    return {
        "signal_id": sig.get("signal_id", ""),
        "title": sig.get("title", ""),
        "summary": sig.get("summary", ""),
        "reasoning": sig.get("reasoning", ""),
        "transmission_chain": sig.get("transmission_chain", []),
        "sentiment_score": sig.get("sentiment_score", 0.0),
        "confidence": sig.get("confidence", 0.0),
        "intensity": sig.get("intensity", 1),
        "expectation_gap": sig.get("expectation_gap", 0.5),
        "timeliness": sig.get("timeliness", 0.5),
        "expected_horizon": sig.get("expected_horizon", "T+0"),
        "price_in_status": sig.get("price_in_status", "未知"),
        "impact_tickers": sig.get("impact_tickers", []),
        "industry_tags": sig.get("industry_tags", []),
        "sources": sig.get("sources", []),
        "search_results": sig.get("search_results", []),
    }


def to_latest_json(
    signals: List[Dict[str, Any]],
    timestamp: Optional[str] = None,
    run_id: Optional[str] = None,
    charts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """將 signal 列表序列化為 latest.json 格式。

    Args:
        signals: InvestmentSignal dict 列表（使用 shared schema 的 model_dump() 格式）
        timestamp: ISO 時間戳記，預設為現在
        run_id: 執行 ID，預設自動產生
        charts: 圖表配置（目前保留空字典）

    Returns:
        latest.json 格式的 dict
    """
    ts = timestamp or datetime.now().isoformat()
    rid = run_id or f"composer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return {
        "generated_at": ts,
        "run_id": rid,
        "count": len(signals),
        "signals": [_serialize_signal(s) for s in signals],
        "charts": charts or {},
    }


def write_latest_json(data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """將 latest.json 寫入檔案。

    Args:
        data: latest.json 格式的 dict
        output_path: 輸出路徑，預設 data/latest.json

    Returns:
        實際寫入的路徑
    """
    if output_path is None:
        output_path = str(Path(__file__).resolve().parents[3] / "data" / "latest.json")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"✅ latest.json written to {path} ({data['count']} signals)")
    return str(path)


def read_latest_json(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """從檔案讀取 latest.json。

    Args:
        path: 檔案路徑，預設 data/latest.json

    Returns:
        latest.json dict，找不到回傳 None
    """
    if path is None:
        path = str(Path(__file__).resolve().parents[3] / "data" / "latest.json")

    p = Path(path)
    if not p.exists():
        logger.warning(f"latest.json not found: {p}")
        return None

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        logger.info(f"📖 latest.json loaded from {p} ({data.get('count', 0)} signals)")
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to read latest.json: {e}")
        return None
