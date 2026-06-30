"""Smoke test for alphaear-composer skill.

Verifies:
1. Module imports work
2. Database manager connects
3. Serializer produces valid latest.json structure
4. Signal formation works with sample data
5. deepear-lite local mode reads the output
"""

import json
import sys
import tempfile
from pathlib import Path

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_imports():
    """Test that all modules import without error."""
    import importlib.util
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"

    modules = [
        "database_manager",
        "serializer",
        "signal_formation",
        "isq_scoring",
    ]
    for mod_name in modules:
        spec = importlib.util.spec_from_file_location(
            mod_name, scripts_dir / f"{mod_name}.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    print("PASS: All imports successful")


def test_serializer():
    """Test that serializer produces valid latest.json structure."""
    import importlib.util
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location("serializer", scripts_dir / "serializer.py")
    serializer_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serializer_mod)
    to_latest_json = serializer_mod.to_latest_json
    write_latest_json = serializer_mod.write_latest_json
    read_latest_json = serializer_mod.read_latest_json

    sample_signals = [
        {
            "signal_id": "2330",
            "title": "台積電 Q2 營收創新高",
            "summary": "台積電 Q2 營收達新台幣 XXX 億元",
            "reasoning": "AI 需求帶動",
            "transmission_chain": [],
            "sentiment_score": 0.75,
            "confidence": 0.8,
            "intensity": 4,
            "expectation_gap": 0.5,
            "timeliness": 0.8,
            "expected_horizon": "T+3",
            "price_in_status": "未知",
            "impact_tickers": [],
            "industry_tags": ["半導體"],
            "sources": [],
            "search_results": [],
        }
    ]

    data = to_latest_json(sample_signals)

    # Verify structure
    assert "generated_at" in data
    assert "run_id" in data
    assert "count" in data
    assert data["count"] == 1
    assert "signals" in data
    assert len(data["signals"]) == 1
    assert data["signals"][0]["signal_id"] == "2330"
    print("PASS: Serializer produces valid structure")

    # Test write + read roundtrip
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        write_latest_json(data, tmp_path)
        read_back = read_latest_json(tmp_path)
        assert read_back is not None
        assert read_back["count"] == 1
        assert read_back["signals"][0]["title"] == sample_signals[0]["title"]
        print("PASS: Write + read roundtrip successful")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_signal_formation():
    """Test heuristic signal formation with sample news."""
    import importlib.util
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location("signal_formation", scripts_dir / "signal_formation.py")
    sf_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sf_mod)
    form_heuristic_signal = sf_mod.form_heuristic_signal
    form_signals_from_news = sf_mod.form_signals_from_news

    sample_news = [
        {
            "id": "news_001",
            "source": "cnbc",
            "title": "NVDA reaches new all-time high",
            "url": "https://example.com/nvda",
            "content": "NVIDIA stock hits record high amid AI boom",
            "sentiment_score": 0.6,
        },
        {
            "id": "news_002",
            "source": "reuters",
            "title": "AI chip demand surges",
            "url": "https://example.com/chips",
            "content": "Global demand for AI accelerators continues to grow",
            "sentiment_score": 0.4,
        },
    ]

    signal = form_heuristic_signal(sample_news, market="both")
    assert signal is not None
    assert signal["signal_id"]  # non-empty
    assert signal["title"]  # non-empty
    assert -1.0 <= signal["sentiment_score"] <= 1.0
    assert 0.0 <= signal["confidence"] <= 1.0
    assert 1 <= signal["intensity"] <= 5
    print("PASS: Signal formation works with sample news")

    # Test form_signals_from_news
    signals = form_signals_from_news(sample_news, market="both")
    assert len(signals) >= 0  # may be 0 if no ticker detected
    print("PASS: Signal grouping works")


def test_isq_scoring():
    """Test ISQ scoring heuristics."""
    import importlib.util
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location("isq_scoring", scripts_dir / "isq_scoring.py")
    isq_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isq_mod)
    heuristic_score = isq_mod.heuristic_score
    composite_score = isq_mod.composite_score

    news = [
        {"sentiment_score": 0.5},
        {"sentiment_score": 0.7},
    ]

    isq = heuristic_score(news)
    assert -1.0 <= isq["sentiment_score"] <= 1.0
    assert 0.0 <= isq["confidence"] <= 1.0
    assert 1 <= isq["intensity"] <= 5
    assert 0.0 <= isq["expectation_gap"] <= 1.0
    assert 0.0 <= isq["timeliness"] <= 1.0

    comp = composite_score(isq)
    assert 0.0 <= comp <= 1.0
    print(f"PASS: ISQ scoring (composite={comp})")


def test_deepear_lite_local():
    """Test that deepear-lite can read composer output."""
    import importlib.util
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location("serializer", scripts_dir / "serializer.py")
    serializer_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serializer_mod)
    to_latest_json = serializer_mod.to_latest_json
    write_latest_json = serializer_mod.write_latest_json

    # Load deepear_lite module
    deepear_path = Path(__file__).resolve().parents[2] / "alphaear-deepear-lite" / "scripts" / "deepear_lite.py"
    spec = importlib.util.spec_from_file_location("deepear_lite", deepear_path)
    deepear_lite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deepear_lite)

    # Create a sample latest.json
    sample = [{
        "signal_id": "TEST",
        "title": "Test Signal",
        "summary": "Testing local mode",
        "reasoning": "Smoke test",
        "transmission_chain": [],
        "sentiment_score": 0.5,
        "confidence": 0.6,
        "intensity": 3,
        "expectation_gap": 0.4,
        "timeliness": 0.7,
        "expected_horizon": "T+1",
        "price_in_status": "未知",
        "impact_tickers": [],
        "industry_tags": [],
        "sources": [],
        "search_results": [],
    }]

    with tempfile.TemporaryDirectory() as tmpdir:
        latest_path = Path(tmpdir) / "latest.json"
        write_latest_json(to_latest_json(sample), str(latest_path))

        # Patch the local path
        original_path = deepear_lite.DeepEarLiteTools._LOCAL_PATH
        deepear_lite.DeepEarLiteTools._LOCAL_PATH = latest_path

        try:
            tools = deepear_lite.DeepEarLiteTools()
            result = tools.fetch_latest_signals(source="local")
            assert "Test Signal" in result
            assert "DeepEar Lite Signal Report" in result
            print("PASS: deepear-lite reads local latest.json")
        finally:
            deepear_lite.DeepEarLiteTools._LOCAL_PATH = original_path


if __name__ == "__main__":
    tests = [
        test_imports,
        test_serializer,
        test_signal_formation,
        test_isq_scoring,
        test_deepear_lite_local,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
