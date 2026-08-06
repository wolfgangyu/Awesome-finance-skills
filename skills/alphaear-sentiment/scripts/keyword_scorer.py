"""Automated keyword-based sentiment scoring for financial news.

Supports:
- zh-TW (Traditional Chinese)
- ja (Japanese)
- en (English, fallback)

Scoring logic:
- Strong positive: +0.5
- Medium positive: +0.2
- Weak positive: +0.1
- Strong negative: -0.5
- Medium negative: -0.2
- Weak negative: -0.1
- Neutral: 0.0

Returns:
- score: float (-1.0 ~ +1.0)
- matched_keywords: list of matched keywords
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from loguru import logger


class KeywordScorer:
    """Automated keyword-based sentiment scorer."""

    def __init__(self):
        self.keywords = self._load_keywords()

    def _load_keywords(self) -> Dict[str, Dict]:
        """Load keyword dictionaries from references/."""
        base_path = Path(__file__).resolve().parent.parent / "references"
        keywords = {}

        # Load zh-TW keywords
        zh_tw_path = base_path / "keywords_zh_tw.json"
        if zh_tw_path.exists():
            try:
                with open(zh_tw_path, "r", encoding="utf-8") as f:
                    keywords["zh-TW"] = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load zh-TW keywords: {e}")

        # Load ja keywords
        ja_path = base_path / "keywords_ja.json"
        if ja_path.exists():
            try:
                with open(ja_path, "r", encoding="utf-8") as f:
                    keywords["ja"] = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load ja keywords: {e}")

        # Fallback English (minimal set)
        keywords["en"] = {
            "positive": {
                "strong": ["surge", "record high", "soar", "boom", "bullish", "upgrade", "acquire", "launch"],
                "medium": ["rise", "gain", "growth", "expand", "improve"],
                "weak": ["slightly up", "marginal gain"]
            },
            "negative": {
                "strong": ["crash", "plunge", "slump", "bankrupt", "fraud", "scandal", "downgrade"],
                "medium": ["fall", "drop", "decline", "loss", "cut"],
                "weak": ["slightly down", "marginal loss"]
            },
            "neutral": ["update", "announce", "report", "meeting", "conference"]
        }

        return keywords

    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character set."""
        if not text:
            return "en"

        # Check for Traditional Chinese characters
        if any(0x4E00 <= ord(c) <= 0x9FFF for c in text):
            return "zh-TW"
        # Check for Hiragana/Katakana/Kanji
        if any(0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF for c in text):
            return "ja"
        # Default to English
        return "en"

    def _score_text(self, text: str, language: str) -> Tuple[float, List[str]]:
        """Score text using keyword matching."""
        if language not in self.keywords:
            language = "en"

        lang_keywords = self.keywords[language]
        score = 0.0
        matched = []

        # Check positive keywords
        for strength, weight in [("strong", 0.5), ("medium", 0.2), ("weak", 0.1)]:
            for keyword in lang_keywords["positive"][strength]:
                if keyword in text:
                    score += weight
                    matched.append(f"pos_{strength}:{keyword}")

        # Check negative keywords
        for strength, weight in [("strong", -0.5), ("medium", -0.2), ("weak", -0.1)]:
            for keyword in lang_keywords["negative"][strength]:
                if keyword in text:
                    score += weight
                    matched.append(f"neg_{strength}:{keyword}")

        # Check neutral keywords (no score impact)
        for keyword in lang_keywords["neutral"]:
            if keyword in text:
                matched.append(f"neutral:{keyword}")

        # Clamp score to [-1.0, 1.0]
        score = max(-1.0, min(1.0, score))
        return score, matched

    def score_news(self, title: str, content: str = "", language: Optional[str] = None) -> Dict:
        """Score a news item."""
        text = f"{title} {content}"

        # Auto-detect language if not provided
        if language is None:
            language = self._detect_language(text)

        score, matched = self._score_text(text, language)

        return {
            "score": round(score, 2),
            "language": language,
            "matched_keywords": matched,
            "reason": f"Keyword-based scoring: {len(matched)} matches found"
        }