"""Light wrapper around pandas BusinessDay for next-N-trading-day queries.

The implementation today is a thin pass-through. Future work may inject TWSE /
NYSE holiday-aware calendars (per spec Task 4 -- future expansion).
"""
from __future__ import annotations

import pandas as pd
from pandas.tseries.offsets import BusinessDay


def next_trading_day(market: str, after: pd.Timestamp, n: int = 1) -> pd.DatetimeIndex:
    """Return ``n`` consecutive business days after ``after``.

    Args:
        market: Free-form market tag ("TW" / "US" / "OTHER"). Currently unused
                beyond validating that it is a string; reserved for future
                holiday-calendar expansion.
        after: A pandas Timestamp marking the inclusive base day.
        n: Number of trading days to return. Defaults to 1.

    Returns:
        pd.DatetimeIndex of length ``n``. Each element is offset by
        ``BusinessDay(i+1)`` from ``after``.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    if not isinstance(after, pd.Timestamp):
        raise TypeError("after must be a pd.Timestamp")
    base = pd.Timestamp(after)
    deltas = [base + BusinessDay(i + 1) for i in range(n)]
    return pd.DatetimeIndex(deltas)
