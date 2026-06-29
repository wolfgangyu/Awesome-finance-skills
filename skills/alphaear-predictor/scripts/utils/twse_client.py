"""台灣股票 TWSE / TPEx 官方 HTTP 客戶端。

只使用 requests，不需要 API key 也沒有附帶其他依賴。
與其他 skill 一樣可以單獨散佈與測試。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

import pandas as pd
import requests


TWSE_DAILY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
TPEX_DAILY_URL = (
    "https://www.tpex.org.tw/web/stock/aftertrading/"
    "daily_trading_info/stock_day.php"
)

# TWSE / TPEx 月報格式欄位對映到 alphaear K 線契約（date, open, high, low, close, volume）。
_FIELD_MAP = {
    "日期": "date",
    "開盤價": "open",
    "最高價": "high",
    "最低價": "low",
    "收盤價": "close",
    "成交股數": "volume",
}


def detect_market(ticker: str) -> Literal["twse", "tpex", "us"]:
    """依 ticker 樣式判斷要走的市場。

    規則：
      - 純字母（含 1~5 個英文）→ 美股，走 yfinance。
      - 4 位純數字 → 台股。TWSE 與 TPEx 用 4 位數字重疊，因此**透過**
        後續呼叫端以 fallback 順序（先 TWSE、再 TPEx）處理，這裡只回
        ``"twse"`` 當預設。
      - 5~6 位純數字 → 預期是舊版台股代碼（已不再使用），降級回 ``"twse"``。
    """
    ticker = ticker.strip()
    if ticker.isalpha():
        return "us"
    return "twse"


def _parse_roc_date(value: str) -> str:
    """把 TWSE/TPEx 回傳的民國日期（例如 114/06/20）轉成 ISO 格式。

    民國年 = 西元年 - 1911。
    """
    parts = value.split("/")
    if len(parts) != 3:
        return value
    roc_year, month, day = parts
    try:
        year = int(roc_year) + 1911
        return datetime(year, int(month), int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return value


def _normalize_kline(df: pd.DataFrame) -> pd.DataFrame:
    """將 TWSE/TPEx 回傳的欄位統一為英文小寫，並把數字字串轉 float。"""
    if df.empty:
        return df
    df = df.rename(columns={k: v for k, v in _FIELD_MAP.items() if k in df.columns})
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .pipe(pd.to_numeric, errors="coerce")
            )
    if "date" in df.columns:
        df["date"] = df["date"].apply(_parse_roc_date)
    return df[[c for c in ("date", "open", "high", "low", "close", "volume") if c in df.columns]]


def fetch_kline_twse(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """取得 TWSE 上市個股的日 K 線。

    Args:
        ticker: 4 位數字股票代號，例如 ``"2330"``（台積電）。
        start_date: ``"YYYY-MM-DD"``，目前僅用於記錄；TWSE 回傳以一個月為單位，
            常用的月報格式以 end_date 為「最近月份」回傳。
        end_date: ``"YYYY-MM-DD"``，對應 TWSE 接受的 ``date`` 參數。
    """
    params = {
        "response": "json",
        "date": end_date.replace("-", "")[:6],
        "stockNo": ticker,
    }
    resp = requests.get(TWSE_DAILY_URL, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("data") or []
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    fields = payload.get("fields") or []
    df = pd.DataFrame(rows, columns=fields)
    return _normalize_kline(df)


def fetch_kline_tpex(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """取得 TPEx 上櫃個股的日 K 線。

    參數契約同 :func:`fetch_kline_twse`。
    """
    # TPEx 對日期採用西元年月，但要 hyphen 分隔
    params = {
        "l": "zh-tw",
        "d": end_date.replace("-", "/"),
        "s": ticker,
        "o": "json",
    }
    resp = requests.get(TPEX_DAILY_URL, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    # TPEx 的格式是 {"tables": [...]}; 容錯舊版 ("data")。
    if "tables" in payload and payload["tables"]:
        table = payload["tables"][0]
        rows = table.get("data") or []
        fields = (table.get("fields") or [])
    else:
        rows = payload.get("data") or []
        fields = payload.get("fields") or []
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows, columns=fields)
    return _normalize_kline(df)


def fetch_kline_with_fallback(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """先試 TWSE，若空資料再試 TPEx。

    適用於無法事先判斷 ticker 屬於上市或上櫃的情境；如果兩邊都沒資料，
    回傳空 DataFrame，並由 caller 決定 fallback（yfinance for 美股）。
    """
    df = fetch_kline_twse(ticker, start_date, end_date)
    if not df.empty:
        df.attrs["_market"] = "twse"
        return df
    df = fetch_kline_tpex(ticker, start_date, end_date)
    if not df.empty:
        df.attrs["_market"] = "tpex"
        return df
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
