"""Smoke tests for training helpers — mock external calls."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]


@pytest.fixture
def mock_trainer_patches() -> dict:
    """Return a dict of mock objects for patching training dependencies."""
    return {
        "SentenceTransformer": MagicMock(),
        "KronosTokenizer": MagicMock(),
        "Kronos": MagicMock(),
        "DatabaseManager": MagicMock(),
        "StockTools": MagicMock(),
        "SearchTools": MagicMock(),
        "get_model": MagicMock(),
    }


@pytest.mark.skipif(torch is None, reason="torch not installed — cannot import training module")
def test_init_loads_models(mock_trainer_patches) -> None:
    """AutoSynthesisTrainer.__init__ should load embedder + Kronos + Tokenizer."""
    from scripts.utils.predictor import training

    with patch.object(training, "SentenceTransformer", mock_trainer_patches["SentenceTransformer"]), \
         patch.object(training, "KronosTokenizer", mock_trainer_patches["KronosTokenizer"]), \
         patch.object(training, "Kronos", mock_trainer_patches["Kronos"]), \
         patch.object(training, "DatabaseManager", mock_trainer_patches["DatabaseManager"]), \
         patch.object(training, "StockTools", mock_trainer_patches["StockTools"]), \
         patch.object(training, "SearchTools", mock_trainer_patches["SearchTools"]), \
         patch.object(training, "get_model", mock_trainer_patches["get_model"]):
        mock_trainer_patches["SentenceTransformer"].return_value = MagicMock()
        mock_trainer_patches["KronosTokenizer"].return_value = MagicMock()
        mock_model = MagicMock()
        mock_model.s1_bits = 10
        mock_model.s2_bits = 10
        mock_model.n_layers = 12
        mock_model.d_model = 256
        mock_model.n_heads = 8
        mock_model.ff_dim = 512
        mock_model.ffn_dropout_p = 0.1
        mock_model.attn_dropout_p = 0.1
        mock_model.resid_dropout_p = 0.1
        mock_model.token_dropout_p = 0.1
        mock_model.learn_te = True
        mock_trainer_patches["Kronos"].from_pretrained.return_value = mock_model

        trainer = training.AutoSynthesisTrainer()
        assert trainer.device is not None
        assert trainer.model is not None
        assert trainer.embedder is not None


@pytest.mark.skipif(torch is None, reason="torch not installed")
def test_save_model_creates_directory_and_file(mock_trainer_patches) -> None:
    from scripts.utils.predictor import training

    with patch.object(training, "SentenceTransformer", mock_trainer_patches["SentenceTransformer"]), \
         patch.object(training, "KronosTokenizer", mock_trainer_patches["KronosTokenizer"]), \
         patch.object(training, "Kronos", mock_trainer_patches["Kronos"]), \
         patch.object(training, "DatabaseManager", mock_trainer_patches["DatabaseManager"]), \
         patch.object(training, "StockTools", mock_trainer_patches["StockTools"]), \
         patch.object(training, "SearchTools", mock_trainer_patches["SearchTools"]), \
         patch.object(training, "get_model", mock_trainer_patches["get_model"]):
        mock_trainer_patches["SentenceTransformer"].return_value = MagicMock()
        mock_trainer_patches["KronosTokenizer"].return_value = MagicMock()
        mock_model = MagicMock()
        mock_model.s1_bits = 10
        mock_model.s2_bits = 10
        mock_model.n_layers = 12
        mock_model.d_model = 256
        mock_model.n_heads = 8
        mock_model.ff_dim = 512
        mock_model.ffn_dropout_p = 0.1
        mock_model.attn_dropout_p = 0.1
        mock_model.resid_dropout_p = 0.1
        mock_model.token_dropout_p = 0.1
        mock_model.learn_te = True
        mock_trainer_patches["Kronos"].from_pretrained.return_value = mock_model

        trainer = training.AutoSynthesisTrainer()
        with tempfile.TemporaryDirectory() as td:
            path = trainer.save_model(path=os.path.join(td, "test.pt"))
            assert os.path.isfile(path)
            # Verify checkpoint structure
            ckpt = torch.load(path, map_location="cpu", weights_only=True)
            assert "news_proj_state_dict" in ckpt
            assert "news_dim" in ckpt
            assert "d_model" in ckpt


@pytest.mark.skipif(torch is None, reason="torch not installed")
def test_save_model_defaults_to_src_dir(mock_trainer_patches) -> None:
    from scripts.utils.predictor import training

    with patch.object(training, "SentenceTransformer", mock_trainer_patches["SentenceTransformer"]), \
         patch.object(training, "KronosTokenizer", mock_trainer_patches["KronosTokenizer"]), \
         patch.object(training, "Kronos", mock_trainer_patches["Kronos"]), \
         patch.object(training, "DatabaseManager", mock_trainer_patches["DatabaseManager"]), \
         patch.object(training, "StockTools", mock_trainer_patches["StockTools"]), \
         patch.object(training, "SearchTools", mock_trainer_patches["SearchTools"]), \
         patch.object(training, "get_model", mock_trainer_patches["get_model"]):
        mock_trainer_patches["SentenceTransformer"].return_value = MagicMock()
        mock_trainer_patches["KronosTokenizer"].return_value = MagicMock()
        mock_model = MagicMock()
        mock_model.s1_bits = 10
        mock_model.s2_bits = 10
        mock_model.n_layers = 12
        mock_model.d_model = 256
        mock_model.n_heads = 8
        mock_model.ff_dim = 512
        mock_model.ffn_dropout_p = 0.1
        mock_model.attn_dropout_p = 0.1
        mock_model.resid_dropout_p = 0.1
        mock_model.token_dropout_p = 0.1
        mock_model.learn_te = True
        mock_trainer_patches["Kronos"].from_pretrained.return_value = mock_model

        trainer = training.AutoSynthesisTrainer()
        path = trainer.save_model()
        assert "exports" in path and "models" in path
