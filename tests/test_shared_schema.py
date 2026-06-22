"""Shared alphaear_schema 跨 skill 的契約測試。"""
import sys
from pathlib import Path


def test_shared_schema_round_trip():
    """確保 _shared/alphaear_schema 提供 Pydantic 模型 InvestmentSignal 並可序列化往返。"""
    src_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(src_root / "skills" / "_shared"))

    from alphaear_schema import InvestmentSignal

    signal = InvestmentSignal(
        signal_id="test_sig",
        title="測試訊號",
        summary="測試摘要",
        reasoning="測試推理",
        transmission_chain=[],
        sentiment_score=0.5,
        confidence=0.8,
        intensity=3,
        expectation_gap=0.2,
        timeliness=0.9,
        expected_horizon="T+1",
        price_in_status="未知",
        impact_tickers=[],
        industry_tags=[],
        sources=[],
    )
    assert signal.signal_id == "test_sig"
    assert signal.title == "測試訊號"
    dumped = signal.model_dump(mode="python")
    assert dumped["signal_id"] == "test_sig"
    assert dumped["title"] == "測試訊號"
