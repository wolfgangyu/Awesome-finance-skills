"""Tests for build_dataset entry — mocked end-to-end."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _make_fake_df(n=90, start_price=100.0):
    """Generate a fake OHLCV DataFrame with 1 shock at index 50."""
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = [start_price * (1.0 + (0.50 if i == 50 else 0.001 * i)) for i in range(n)]
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": [c * 0.99 for c in close],
        "close": close,
        "high": [c * 1.01 for c in close],
        "low": [c * 0.98 for c in close],
        "volume": [1000000] * n,
        "change_pct": [0.0] + [(close[i] - close[i-1]) / close[i-1] * 100 for i in range(1, n)],
    })
    return df


class TestBuildDatasetStandalone:
    """Import test — ensure build_dataset.py can be imported without real network."""

    def test_import_build_dataset(self) -> None:
        """build_dataset.py should define main() and a few top-level functions."""
        from scripts import build_dataset  # noqa: F401
        assert hasattr(build_dataset, "main")


class TestBuildDatasetIntegration:
    """Mocked end-to-end: fake DF -> shock -> news -> parquet."""

    @pytest.fixture
    def mock_stock_tools(self) -> MagicMock:
        st = MagicMock()
        st.get_stock_price.side_effect = lambda t, **kw: _make_fake_df(90) if t in ("2330", "AAPL") else pd.DataFrame()
        return st

    @pytest.fixture
    def mock_news_source(self) -> MagicMock:
        ns = MagicMock()
        ns.collect.return_value = [MagicMock(title="Test news", url="https://test.com/1", body="test", published_at="2024-03-01")]
        return ns

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        llm = MagicMock()
        llm.run.return_value.content = '{"is_causal": true, "summary": "Test causal"}'
        return llm

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        emb = MagicMock()
        emb.encode.return_value = [0.1] * 384
        return emb

    def test_discover_shocks_find_one(self, mock_stock_tools) -> None:
        from scripts.build_dataset import discover_shocks
        shocks, skipped = discover_shocks(mock_stock_tools, ["2330"], threshold=2.0, days=365, pred_len=5)
        assert len(shocks) >= 1

    def test_skipped_tickers_returned(self, mock_stock_tools) -> None:
        from scripts.build_dataset import discover_shocks
        # Ticker "NOPE" returns empty DF -> should be skipped
        mock_stock_tools.get_stock_price.side_effect = lambda t, **kw: _make_fake_df(90) if t in ("2330", "AAPL") else pd.DataFrame()
        shocks, skipped = discover_shocks(mock_stock_tools, ["NOPE"], threshold=2.0, days=365, pred_len=5)
        assert shocks == []
        assert len(skipped) == 1
        assert skipped[0]["code"] == "NOPE"

    def test_write_parquet_produces_file(self, tmp_data_dir: Path) -> None:
        from scripts.build_dataset import write_parquet
        dataset = [
            {
                "ticker": "2330",
                "market": "TW",
                "shock_date": "2024-01-15",
                "history_rows": [],
                "target_rows": [],
                "news_text": "test news",
                "news_emb": [0.1] * 384,
                "causality": "verified",
                "unverified_reason": None,
            }
        ]
        try:
            result = write_parquet(dataset, tmp_data_dir)
        except ImportError as exc:
            if "parquet" in str(exc).lower():
                pytest.skip("pyarrow/fastparquet not installed — parquet write skipped")
            raise
        assert result.exists()
        # Only verify if parquet engine is available
        try:
            df = pd.read_parquet(result)
            assert len(df) == 1
            assert df.iloc[0]["ticker"] == "2330"
        except ImportError:
            pytest.skip("pyarrow/fastparquet not installed — parquet read skipped")

    def test_write_skipped_produces_file(self, tmp_data_dir: Path) -> None:
        from scripts.build_dataset import write_skipped
        skipped = [{"code": "NOPE", "reason": "no_history"}]
        result = write_skipped(skipped, tmp_data_dir)
        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["code"] == "NOPE"

    def test_detect_market_used_in_discover(self, mock_stock_tools) -> None:
        """discover_shocks should classify market using detect_market()."""
        from scripts.build_dataset import discover_shocks
        # Return a DF with enough rows so it passes the history check,
        # but the ticker is CRYPTO -> should be skipped as unsupported_market
        mock_stock_tools.get_stock_price.side_effect = lambda t, **kw: _make_fake_df(90) if t == "BTC-USD" else pd.DataFrame()
        shocks, skipped = discover_shocks(mock_stock_tools, ["BTC-USD"], threshold=2.0, days=365, pred_len=5)
        # BTC-USD should be CRYPTO -> skipped
        assert len(skipped) == 1
        assert skipped[0]["reason"] == "unsupported_market"
