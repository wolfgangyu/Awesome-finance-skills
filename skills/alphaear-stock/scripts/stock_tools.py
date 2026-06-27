"""金融分析股票工具 —— 台灣股市（TWSE/TPEx） + 美國股市（yfinance）。

支援：
  - 台灣股市：上市（TWSE）、上櫃（TPEx）
  - 美國股市：yfinance

不再支援：
  - A 股、港股（akshare + EastMoneyDirect 移除）
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import sqlite3
import pandas as pd
import requests
import yfinance as yf
from loguru import logger
from .database_manager import DatabaseManager
from .twse_client import (
    detect_market,
    fetch_kline_with_fallback,
)


class StockTools:
    """金融分析股票工具 —— 結合高性能資料庫快取與增量更新。

    台灣股市：TWSE/TPEx 官方 HTTP
    美國股市：yfinance
    """

    def __init__(self, db: DatabaseManager, auto_update: bool = True):
        self.db = db
        if auto_update:
            self._check_and_update_stock_list()

    def _check_and_update_stock_list(self, force: bool = False):
        """檢查並更新股票列表。

        台灣股市：
          - TWSE 上市：從 https://isin.twse.com.tw/isin/C_public.jsp?strMode=2 抓取
          - TPEx 上櫃：從 https://isin.twse.com.tw/isin/C_public.jsp?strMode=4 抓取
        美國股市：
          - 直接用 yfinance 取得 S&P 500 成分股

        目前僅在列表為空或 force=True 時更新。
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stock_list")
        count = cursor.fetchone()[0]

        if count > 0 and not force:
            logger.info(f"ℹ️ Stock list already cached ({count} stocks)")
            return

        logger.info("📡 Updating TWSE/TPEx + US stock list...")

        # === 台灣股市：TWSE + TPEx ===
        twse_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        tpex_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"

        def fetch_tw_list(url: str) -> pd.DataFrame:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            df = pd.read_html(resp.text)[0]
            df.columns = df.iloc[0]
            df = df.drop(0).copy()
            df = df[df["有價證券代號及名稱"].str.contains(r"^[0-9]{4,6}\s")]
            df["code"] = df["有價證券代號及名稱"].str.extract(r"^(\d+)")
            df["name"] = df["有價證券代號及名稱"].str.extract(r"\s(.+)$")
            return df[["code", "name"]]

        df_twse = fetch_tw_list(twse_url)
        df_tpex = fetch_tw_list(tpex_url)
        df_tw = pd.concat([df_twse, df_tpex], ignore_index=True)

        # === 美國股市：yfinance ===
        try:
            sp500 = yf.Ticker("^GSPC")
            sp500_comps = sp500.history(period="1d")
            sp500_tickers = sp500_comps.attrs.get("components", {})
            df_us = pd.DataFrame({
                "code": list(sp500_tickers.keys()),
                "name": list(sp500_tickers.values()),
            })
        except Exception as e:
            logger.warning(f"⚠️ yfinance US stock list failed: {e}")
            df_us = pd.DataFrame(columns=["code", "name"])

        df_combined = pd.concat([df_tw, df_us], ignore_index=True)
        if not df_combined.empty:
            self.db.save_stock_list(df_combined)
            logger.info(f"✅ Cached {len(df_combined)} stocks to database.")

    def search_ticker(self, query: str, limit: int = 5) -> List[Dict]:
        """模糊搜尋台灣/美國股票代號或名稱。

        Args:
            query: 股票代號或名稱，例如 "2330"、"台積電"、"AAPL"、"Apple"。
            limit: 回傳筆數上限。

        Returns:
            List[Dict]: 每個元素為 {"code": str, "name": str}。
        """
        clean_query = re.sub(r"\.(SZ|SH|HK|US)$", "", query, flags=re.IGNORECASE)
        clean_query = re.sub(r"[^a-zA-Z0-9一-鿿]", "", clean_query)

        # 常見美股縮寫（不再支援 A 股/港股縮寫）
        aliases = {
            "AAPL": "Apple",
            "MSFT": "Microsoft",
            "GOOGL": "Alphabet",
            "AMZN": "Amazon",
            "TSLA": "Tesla",
            "META": "Meta",
            "NVDA": "NVIDIA",
            "TSM": "Taiwan Semiconductor",
        }
        search_query = aliases.get(clean_query.upper(), clean_query)

        # 先試資料庫
        res = self.db.search_stock(search_query, limit)
        if res:
            return res

        # 如果資料庫沒有，直接回 mock 美股（台股必須在資料庫內）
        if clean_query.isalpha() and len(clean_query) <= 5:
            return [{"code": clean_query.upper(), "name": clean_query.upper()}]
        return []

    def get_stock_price(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_sync: bool = False,
    ) -> pd.DataFrame:
        """取得指定股票的歷史價格資料。

        依 ticker 判斷市場：
          - 台灣股市（TWSE/TPEx）：走 twse_client.fetch_kline_with_fallback()
          - 美國股市：走 yfinance

        Args:
            ticker: 股票代號，例如 "2330"（台積電）、"AAPL"（蘋果）。
            start_date: 開始日期，格式 "YYYY-MM-DD"。預設為 90 天前。
            end_date: 結束日期，格式 "YYYY-MM-DD"。預設為今天。
            force_sync: 強制從網路更新，即使資料庫已有資料。

        Returns:
            pd.DataFrame: 套件含 date, open, close, high, low, volume, change_pct 欄位。
        """
        now = datetime.now()
        if not end_date:
            end_date = now.strftime("%Y-%m-%d")
        if not start_date:
            start_date = (now - timedelta(days=90)).strftime("%Y-%m-%d")

        df_db = self.db.get_stock_prices(ticker, start_date, end_date)

        need_update = False
        if df_db.empty:
            need_update = True
        else:
            db_latest = pd.to_datetime(df_db["date"].max())
            req_latest = pd.to_datetime(end_date)
            if (req_latest - db_latest).days > 2:
                need_update = True

        if force_sync:
            need_update = True

        if need_update:
            market = detect_market(ticker)
            if market == "us":
                df_remote = self._fetch_us_kline(ticker, start_date, end_date)
            else:
                df_remote = fetch_kline_with_fallback(ticker, start_date, end_date)
                # TWSE/TPEx API 回傳最近一個月資料，不受 start_date/end_date 限制
                # 過濾至請求範圍內，避免寫入超出請求範圍的舊年份資料
                df_remote = df_remote.loc[
                    (df_remote["date"] >= start_date) & (df_remote["date"] <= end_date)
                ].copy()
                if not df_remote.empty and "change_pct" not in df_remote.columns:
                    df_remote["change_pct"] = df_remote["close"].astype(float).pct_change() * 100
                    df_remote["change_pct"] = df_remote["change_pct"].fillna(0)

            if not df_remote.empty:
                # 嘗試寫入 DB；失敗時回退到 remote 原始資料，避免錯誤蔓延
                try:
                    self.db.save_stock_prices(ticker, df_remote)
                    return self.db.get_stock_prices(ticker, start_date, end_date)
                except (KeyError, sqlite3.Error) as db_err:
                    logger.warning(f"⚠️ Save prices failed for {ticker}: {db_err}")

            return df_remote

        return df_db

    def _fetch_us_kline(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """取得美國股市 K 線（yfinance）。"""
        try:
            yf_ticker = yf.Ticker(ticker)
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            df_us = yf_ticker.history(start=start_date, end=end_dt.strftime("%Y-%m-%d"))
            if df_us.empty:
                return pd.DataFrame()

            df_us = df_us.reset_index()
            date_col = "Date" if "Date" in df_us.columns else df_us.columns[0]
            df_us = df_us.rename(columns={
                "Open": "open",
                "Close": "close",
                "High": "high",
                "Low": "low",
                "Volume": "volume",
            })

            if pd.api.types.is_datetime64_any_dtype(df_us[date_col]):
                df_us["date"] = df_us[date_col].dt.strftime("%Y-%m-%d")
            else:
                df_us["date"] = pd.to_datetime(df_us[date_col]).dt.strftime("%Y-%m-%d")

            df_us["change_pct"] = df_us["close"].pct_change() * 100
            df_us["change_pct"] = df_us["change_pct"].fillna(0)

            return df_us[["date", "open", "close", "high", "low", "volume", "change_pct"]]
        except Exception as e:
            logger.error(f"❌ yfinance failed for {ticker}: {e}")
            return pd.DataFrame()

    def get_stock_fundamentals(self, ticker: str) -> Dict:
        """取得公司基本面資料。

        目前僅支援美國股市（yfinance）；台灣股市回空 dict，待後續整合 My-TW-Coverage。

        Args:
            ticker: 股票代號，例如 "AAPL"、"2330"。

        Returns:
            Dict: 套件含 name, sector, industry, market_cap, pe_ratio, summary, currency 欄位。
        """
        market = detect_market(ticker)
        if market != "us":
            return {}

        try:
            tk = yf.Ticker(ticker)
            info = tk.info
            if not info or "longName" not in info:
                logger.warning(f"⚠️ No fundamental data found for US stock: {ticker}")
                return {}
            return {
                "name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "summary": (info.get("longBusinessSummary", "")[:300] + "...")
                if info.get("longBusinessSummary")
                else "",
                "currency": info.get("currency"),
            }
        except Exception as e:
            logger.error(f"❌ yfinance fundamentals failed for {ticker}: {e}")
            return {}


def get_stock_analysis(ticker: str, db: DatabaseManager) -> str:
    """生成指定股票的分析摘要報告。

    Args:
        ticker: 股票代號
        db: 資料庫管理器實例

    Returns:
        str: Markdown 格式的分析報告，套件含價格走勢和關鍵指標。
    """
    tools = StockTools(db)
    df = tools.get_stock_price(ticker)

    if df.empty:
        return f"❌ 未能取得 {ticker} 的股價資料。"

    latest = df.iloc[-1]
    change = ((latest["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"]) * 100

    report = [
        f"## 📊 {ticker} 分析報告",
        f"- **查詢時段**: {df.iloc[0]['date']} -> {latest['date']}",
        f"- **當前價**: ${latest['close']:.2f}",
        f"- **時段漲跌**: {change:+.2f}%",
        f"- **最高/最低**: ${df['high'].max():.2f} / ${df['low'].min():.2f}",
        "\n### 最近交易概覽",
        "```",
        df.tail(5)[["date", "close", "change_pct", "volume"]].to_string(index=False),
        "```",
    ]
    return "\n".join(report)