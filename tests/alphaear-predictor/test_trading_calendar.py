"""trading_calendar wrapper tests — wrapped pd.offsets.BusinessDay baseline."""
from __future__ import annotations

import pandas as pd

from scripts.utils.trading_calendar import next_trading_day


def test_default_returns_business_day_offset() -> None:
    # Friday -> Monday (pandas BusinessDay skips Sat/Sun)
    out = next_trading_day("US", pd.Timestamp("2025-07-04"), n=1)
    assert isinstance(out, pd.DatetimeIndex)
    assert len(out) == 1
    assert out[0].dayofyear == pd.Timestamp("2025-07-07").dayofyear


def test_n_returns_n_consecutive_business_days() -> None:
    out = next_trading_day("TW", pd.Timestamp("2025-07-04"), n=3)
    assert len(out) == 3
    # all returned days must be weekdays
    assert all(d.dayofweek < 5 for d in out)


def test_invalid_market_falls_back_to_business_day() -> None:
    out = next_trading_day("OTHER", pd.Timestamp("2025-07-04"), n=1)
    assert len(out) == 1
    assert out[0].dayofweek < 5
