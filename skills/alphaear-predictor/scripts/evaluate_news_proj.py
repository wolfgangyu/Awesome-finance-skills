"""Stage 3: Evaluate trained news_proj model on held-out shocks.

Entry point:
    python scripts/evaluate_news_proj.py --model exports/models/kronos_news_latest.pt --us-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils.market_detect import detect_market, resolve_name


def discover_eval_shocks(
    stock_tools,
    tickers: List[str],
    pred_len: int = 5,
    threshold: float = 2.0,
    days: int = 365,
) -> List[dict]:
    """Discover shocks for evaluation (same logic as build_dataset but simpler)."""
    shocks = []
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    for ticker in tickers:
        df = stock_tools.get_stock_price(ticker, start_date=start_date, end_date=end_date)
        if df.empty or len(df) < 60:
            continue

        if "change_pct" not in df.columns:
            df = df.copy()
            df["change_pct"] = df["close"].astype(float).pct_change() * 100
            df["change_pct"] = df["change_pct"].fillna(0)

        market = detect_market(ticker)
        if market not in ("TW", "US"):
            continue

        moves = df[df["change_pct"].abs() > threshold]
        for idx, row in moves.iterrows():
            date_idx = df.index.get_loc(idx)
            if date_idx < 50 or date_idx + pred_len > len(df):
                continue

            shocks.append({
                "ticker": ticker,
                "market": market,
                "date": str(row["date"]),
                "change": float(row["change_pct"]),
                "history": df.iloc[max(0, date_idx - 50):date_idx],
                "target": df.iloc[date_idx:date_idx + pred_len],
            })

    return shocks


def evaluate(
    trainer,
    model_path: str,
    shocks: List[dict],
    pred_len: int = 5,
) -> dict:
    """Evaluate base vs news-aware prediction on shocks.

    Returns results dict with per-shock MAEs and group averages.
    """
    import numpy as np
    import torch

    # Load weights
    try:
        loaded = torch.load(model_path, map_location=trainer.device, weights_only=True)
        if "news_proj_state_dict" in loaded:
            if hasattr(trainer.model, "news_proj") and trainer.model.news_proj is not None:
                trainer.model.news_proj.load_state_dict(loaded["news_proj_state_dict"])
    except Exception as exc:
        logger.warning("Failed to load model weights from %s: %s", model_path, exc)

    # Lazy import KronosPredictor
    from utils.predictor.kronos import KronosPredictor
    predictor = KronosPredictor(trainer.model, trainer.tokenizer, device=trainer.device)

    results = []
    base_maes = []
    news_maes = []
    verified_base_maes = []
    verified_news_maes = []
    unverified_base_maes = []
    unverified_news_maes = []

    print("\n" + "=" * 90)
    print(f"{'Date':<12} | {'Ticker':<8} | {'Base MAE':<15} | {'News MAE':<15} | {'Improvement'}")
    print("-" * 90)

    for shock in shocks:
        h = shock["history"]
        t = shock["target"]
        actuals = t["close"].values[:pred_len]

        x_ts = pd.to_datetime(h["date"])
        future_dates = pd.date_range(start=x_ts.iloc[-1] + pd.Timedelta(days=1), periods=pred_len, freq="B")
        y_ts = pd.Series(future_dates)

        # Base prediction
        p_base = predictor.predict(h, x_ts, y_ts, pred_len=pred_len, news_emb=None, verbose=False)
        b_preds = p_base["close"].values[:len(actuals)]

        # News-aware prediction (dummy embedding for eval — use zero vector)
        p_news = predictor.predict(h, x_ts, y_ts, pred_len=pred_len, news_emb=np.zeros(384), verbose=False)
        n_preds = p_news["close"].values[:len(actuals)]

        b_mae = float(np.mean(np.abs(b_preds - actuals)))
        n_mae = float(np.mean(np.abs(n_preds - actuals)))

        base_maes.append(b_mae)
        news_maes.append(n_mae)

        # Track verified/unverified separately
        causality = shock.get("causality", "verified")
        if causality == "verified":
            verified_base_maes.append(b_mae)
            verified_news_maes.append(n_mae)
        else:
            unverified_base_maes.append(b_mae)
            unverified_news_maes.append(n_mae)

        improvement = (b_mae - n_mae) / (b_mae + 1e-6) * 100

        date_str = str(t["date"].values[0])[:10]
        ticker = h.iloc[-1].get("ticker", "Stock") if "ticker" in h.columns else shock["ticker"]
        print(f"{date_str:<12} | {ticker:<8} | {b_mae:<15.4f} | {n_mae:<15.4f} | {improvement:>+7.1f}%")

    # Summary
    avg_base_err = sum(base_maes) / max(1, len(base_maes))
    avg_news_err = sum(news_maes) / max(1, len(news_maes))
    overall_imp = (avg_base_err - avg_news_err) / (avg_base_err + 1e-6) * 100

    print("-" * 90)
    print(f"{'AVERAGE':<12} | {'-':<8} | {avg_base_err:<15.4f} | {avg_news_err:<15.4f} | {overall_imp:>+7.1f}%")
    print("=" * 90 + "\n")

    # Group stats
    group_stats = {}
    if verified_base_maes:
        vb_avg = sum(verified_base_maes) / len(verified_base_maes)
        vn_avg = sum(verified_news_maes) / len(verified_news_maes)
        group_stats["verified"] = {
            "base_mae": vb_avg,
            "news_mae": vn_avg,
            "improvement": (vb_avg - vn_avg) / (vb_avg + 1e-6) * 100,
            "count": len(verified_base_maes),
        }
    if unverified_base_maes:
        ub_avg = sum(unverified_base_maes) / len(unverified_base_maes)
        un_avg = sum(unverified_news_maes) / len(unverified_news_maes)
        group_stats["unverified"] = {
            "base_mae": ub_avg,
            "news_mae": un_avg,
            "improvement": (ub_avg - un_avg) / (ub_avg + 1e-6) * 100,
            "count": len(unverified_base_maes),
        }

    report = {
        "average": {
            "base_mae": avg_base_err,
            "news_mae": avg_news_err,
            "improvement_pct": overall_imp,
            "count": len(shocks),
        },
        "group_stats": group_stats,
        "timestamp": datetime.now().isoformat(),
    }

    # Save summary
    output_dir = _SCRIPTS_DIR / "exports" / "training_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = output_dir / f"eval_summary_{ts}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("Summary saved to %s", summary_path)
    return report


def _lazy_auto_synthesis_trainer():
    """Lazy-import AutoSynthesisTrainer to avoid torch dependency at import time."""
    from utils.predictor.training import AutoSynthesisTrainer
    return AutoSynthesisTrainer


def _lazy_stock_tools():
    """Lazy-import StockTools to avoid torch dependency at import time."""
    try:
        from utils.stock_tools import StockTools
        return StockTools(db=None)
    except Exception:
        class _Dummy:
            def get_stock_price(self, ticker, **kw):
                return pd.DataFrame()
        return _Dummy()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Evaluate trained news_proj model.")
    parser.add_argument("--model", required=True, help="Path to .pt file or 'latest'")
    parser.add_argument("--tickers", nargs="+", default=None, help="Tickers to evaluate, or None for all from DB")
    parser.add_argument("--pred-len", type=int, default=5, help="Prediction length")
    parser.add_argument("--days", type=int, default=365, help="Lookback days for shock discovery")
    parser.add_argument("--threshold", type=float, default=2.0, help="Shock threshold")
    parser.add_argument("--us-only", action="store_true", help="Only evaluate US tickers")
    parser.add_argument("--tw-only", action="store_true", help="Only evaluate TW tickers")

    args = parser.parse_args()

    trainer = _lazy_auto_synthesis_trainer()()

    # Resolve model path
    if args.model == "latest":
        models_dir = _SCRIPTS_DIR / "exports" / "models"
        model_files = list(models_dir.glob("kronos_news_*.pt"))
        if not model_files:
            logger.error("No trained models found in exports/models/")
            sys.exit(1)
        model_path = max(model_files, key=os.path.getctime)
    else:
        model_path = args.model

    if not os.path.isfile(model_path):
        logger.error("Model file not found: %s", model_path)
        sys.exit(1)

    # Resolve tickers
    if args.tickers:
        tickers = args.tickers
    else:
        try:
            from utils.database_manager import DatabaseManager
            db = DatabaseManager()
            res = db.execute_query("SELECT code FROM stock_list")
            tickers = [row["code"] for row in res]
        except Exception:
            tickers = []

    # Filter by market
    if args.us_only:
        tickers = [t for t in tickers if detect_market(t) == "US"]
    elif args.tw_only:
        tickers = [t for t in tickers if detect_market(t) == "TW"]

    stock_tools = _lazy_stock_tools()
    shocks = discover_eval_shocks(stock_tools, tickers, pred_len=args.pred_len, threshold=args.threshold, days=args.days)

    if not shocks:
        logger.warning("No shocks found for evaluation.")
        return

    logger.info("Evaluating %d shocks...", len(shocks))
    report = evaluate(trainer, model_path, shocks, pred_len=args.pred_len)
    logger.info("Evaluation complete. Report: %s", json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
