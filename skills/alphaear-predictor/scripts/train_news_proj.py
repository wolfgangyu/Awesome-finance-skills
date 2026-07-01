"""Stage 2: Train news_proj layer on pre-built dataset.

Entry point:
    python scripts/train_news_proj.py --dataset data/training_dataset.parquet --epochs 30 --lr 1e-3
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

# Ensure scripts/ is on sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _lazy_auto_synthesis_trainer():
    """Lazy-import AutoSynthesisTrainer to avoid torch dependency at import time."""
    from utils.predictor.training import AutoSynthesisTrainer
    return AutoSynthesisTrainer


def backup_and_replace(src_dir: Path, dest_path: Path, out_name: str) -> Optional[str]:
    """Backup existing latest .pt and write new one.

    Returns the backup path, or None if no backup was needed.
    """
    backup_path = None
    existing_latest = src_dir / "kronos_news_latest.txt"
    if existing_latest.exists():
        old_name = existing_latest.read_text(encoding="utf-8").strip()
        old_path = src_dir / old_name
        if old_path.exists():
            backup_dir = src_dir / "_backup"
            backup_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{old_name}_{ts}.pt"
            shutil.copy2(str(old_path), str(backup_path))
            logger.info("Backed up %s -> %s", old_path, backup_path)

    # Write new checkpoint
    os.makedirs(src_dir, exist_ok=True)
    torch_save(dest_path, str(src_dir / f"{out_name}.pt"))

    # Update latest.txt
    latest_path = src_dir / "kronos_news_latest.txt"
    latest_path.write_text(f"{out_name}.pt", encoding="utf-8")

    return backup_path


def torch_save(state_dict, path):
    """Lazy-import torch to save, avoiding hard dependency at import time."""
    import torch
    torch.save(state_dict, path)


def train(
    trainer: "AutoSynthesisTrainer",
    dataset: pd.DataFrame,
    epochs: int = 30,
    lr: float = 1e-3,
    seed: int = 42,
    pred_len: int = 5,
    resume_path: Optional[str] = None,
    out_name: str = "kronos_news_v1",
) -> dict:
    """Core training loop. Returns training report dict."""
    import torch
    import torch.nn as nn

    # Seed
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.backends.cudnn.deterministic = True

    # Resume from existing weights
    if resume_path and os.path.isfile(resume_path):
        try:
            checkpoint = torch.load(resume_path, map_location=trainer.device, weights_only=True)
            if "news_proj_state_dict" in checkpoint:
                if not hasattr(trainer.model, "news_proj") or trainer.model.news_proj is None:
                    news_dim = checkpoint.get("news_dim", 384)
                    trainer.model.news_proj = nn.Linear(news_dim, trainer.model.d_model).to(trainer.device)
                trainer.model.news_proj.load_state_dict(checkpoint["news_proj_state_dict"])
                logger.info("Resumed from %s", resume_path)
            else:
                logger.warning("Checkpoint %s missing 'news_proj_state_dict'. Starting fresh.", resume_path)
        except Exception as exc:
            logger.warning("Failed to resume from %s: %s. Starting fresh.", resume_path, exc)

    # Freeze base model
    for param in trainer.model.parameters():
        param.requires_grad = False
    if trainer.model.news_proj is not None:
        for param in trainer.model.news_proj.parameters():
            param.requires_grad = True

    optimizer = torch.optim.Adam(trainer.model.news_proj.parameters(), lr=lr)
    criterion = torch.nn.CrossEntropyLoss()

    loss_history = []
    best_loss = float("inf")
    best_weights = None

    logger.info("Training for %d epochs...", epochs)

    for epoch in range(epochs):
        total_loss = 0.0
        count = 0
        trainer.model.train()

        for idx, row in dataset.iterrows():
            try:
                history = json.loads(row["history_rows"])
                target = json.loads(row["target_rows"])
                news_emb = json.loads(row["news_emb"])

                hist_raw = pd.DataFrame(history)[["open", "high", "low", "close", "volume"]].values.astype("float32")
                hist_raw = _np_column_stack([hist_raw, hist_raw[:, 3] * hist_raw[:, 4]])

                mean = hist_raw.mean(axis=0)
                std = hist_raw.std(axis=0) + 1e-5
                hist_norm = torch.from_numpy((hist_raw - mean) / std).unsqueeze(0).to(trainer.device)

                target_raw = pd.DataFrame(target)[["open", "high", "low", "close", "volume"]].values.astype("float32")
                target_raw = _np_column_stack([target_raw, target_raw[:, 3] * target_raw[:, 4]])
                target_norm = torch.from_numpy((target_raw - mean) / std).unsqueeze(0).to(trainer.device)

                with torch.no_grad():
                    z_indices = trainer.tokenizer.encode(hist_norm, half=True)
                    t_indices = trainer.tokenizer.encode(target_norm, half=True)
                    s1_ids, s2_ids = z_indices[0], z_indices[1]
                    t_s1, t_s2 = t_indices[0], t_indices[1]

                news_t = torch.tensor(news_emb, dtype=torch.float32).unsqueeze(0).to(trainer.device)
                s1_logits, s2_logits = trainer.model(
                    s1_ids, s2_ids, news_emb=news_t, use_teacher_forcing=True, s1_targets=t_s1
                )

                loss = (criterion(s1_logits[:, -1, :], t_s1[:, 0]) + criterion(s2_logits[:, -1, :], t_s2[:, 0])) / 2
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

                total_loss += loss.item()
                count += 1
            except Exception as exc:
                logger.warning("Skipping row %s due to error: %s", idx, exc)
                continue

        avg_loss = total_loss / max(count, 1)
        loss_history.append(avg_loss)

        if avg_loss < best_loss:
            best_loss = avg_loss
            best_weights = {k: v.clone() for k, v in trainer.model.news_proj.state_dict().items()}

        if (epoch + 1) % 10 == 0:
            logger.info("Epoch %d/%d Loss: %.4f", epoch + 1, epochs, avg_loss)

    # Restore best weights
    if best_weights is not None:
        trainer.model.news_proj.load_state_dict(best_weights)

    # Save
    src_dir = _SCRIPTS_DIR / "exports" / "models"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"kronos_news_{out_name}_{timestamp}.pt"
    out_path = src_dir / out_filename

    backup = backup_and_replace(src_dir, out_path, out_filename)

    report = {
        "epochs": epochs,
        "lr": lr,
        "seed": seed,
        "best_loss": float(best_loss),
        "loss_history": loss_history,
        "dataset_rows": len(dataset),
        "output_path": str(out_path),
        "backup_path": str(backup) if backup else None,
        "timestamp": timestamp,
    }

    report_path = src_dir.parent / "training_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.success("Training complete. Best loss: %.4f", best_loss)
    logger.info("Report saved to %s", report_path)
    return report


def _np_column_stack(arrays):
    """Lazy numpy column_stack to avoid hard torch/numpy import at module level."""
    import numpy as np
    return np.column_stack(arrays)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Train news_proj layer on pre-built dataset.")
    parser.add_argument("--dataset", required=True, help="Path to training_dataset.parquet")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--pred-len", type=int, default=5, help="Prediction length")
    parser.add_argument("--resume", type=str, default=None, help="Path to existing .pt for warm start")
    parser.add_argument("--out-name", type=str, default="v1", help="Output name prefix")
    parser.add_argument("--dry", action="store_true", help="Run forward pass only, don't update weights")

    args = parser.parse_args()

    if not os.path.isfile(args.dataset):
        logger.error("Dataset not found: %s", args.dataset)
        sys.exit(1)

    dataset_df = pd.read_parquet(args.dataset)
    if args.dry:
        logger.info("Dry run mode — no weight updates.")
        report = {"dry_run": True, "dataset_rows": len(dataset_df)}
        logger.info(json.dumps(report, indent=2))
        return

    trainer = _lazy_auto_synthesis_trainer()()
    report = train(
        trainer,
        dataset_df,
        epochs=args.epochs,
        lr=args.lr,
        seed=args.seed,
        pred_len=args.pred_len,
        resume_path=args.resume,
        out_name=args.out_name,
    )
    logger.info("Training report: %s", json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
