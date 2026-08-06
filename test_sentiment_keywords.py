"""
Test script for keyword scoring functionality
"""
import sys
import os
import json

# Add the correct path to Python path
sys.path.insert(0, os.path.abspath('.'))

def load_keywords():
    """Load keyword dictionaries"""
    base_path = os.path.join(os.path.dirname(__file__), 'skills', 'alphaear-sentiment', 'references')

    # Load zh-TW keywords
    zh_tw_path = os.path.join(base_path, 'keywords_zh_tw.json')
    with open(zh_tw_path, 'r', encoding='utf-8') as f:
        zh_tw_keywords = json.load(f)

    # Load ja keywords
    ja_path = os.path.join(base_path, 'keywords_ja.json')
    with open(ja_path, 'r', encoding='utf-8') as f:
        ja_keywords = json.load(f)

    return {
        'zh-TW': zh_tw_keywords,
        'ja': ja_keywords,
        'en': {
            'positive': {
                'strong': ['surge', 'record high', 'soar', 'boom', 'bullish', 'upgrade', 'acquire', 'launch'],
                'medium': ['rise', 'gain', 'growth', 'expand', 'improve'],
                'weak': ['slightly up', 'marginal gain']
            },
            'negative': {
                'strong': ['crash', 'plunge', 'slump', 'bankrupt', 'fraud', 'scandal', 'downgrade'],
                'medium': ['fall', 'drop', 'decline', 'loss', 'cut'],
                'weak': ['slightly down', 'marginal loss']
            },
            'neutral': ['update', 'announce', 'report', 'meeting', 'conference']
        }
    }

def detect_language(text):
    """Improved language detection"""
    if not text:
        return 'en'

    # Count Traditional Chinese characters
    zh_chars = sum(1 for c in text if 0x4E00 <= ord(c) <= 0x9FFF)

    # Count Japanese characters (Hiragana/Katakana/Kanji)
    ja_chars = sum(1 for c in text if 0x3040 <= ord(c) <= 0x30FF)  # Hiragana/Katakana
    ja_chars += sum(1 for c in text if 0x4E00 <= ord(c) <= 0x9FFF)  # Kanji

    # If both have characters, use the one with more
    if zh_chars > 0 and ja_chars > 0:
        return 'zh-TW' if zh_chars >= ja_chars else 'ja'
    elif zh_chars > 0:
        return 'zh-TW'
    elif ja_chars > 0:
        return 'ja'

    # Default to English
    return 'en'

def score_text(text, language, keywords):
    """Score text using keyword matching"""
    if language not in keywords:
        language = 'en'

    lang_keywords = keywords[language]
    score = 0.0
    matched = []

    # Check positive keywords
    for strength, weight in [('strong', 0.5), ('medium', 0.2), ('weak', 0.1)]:
        for keyword in lang_keywords['positive'][strength]:
            if keyword in text:
                score += weight
                matched.append(f'pos_{strength}:{keyword}')

    # Check negative keywords
    for strength, weight in [('strong', -0.5), ('medium', -0.2), ('weak', -0.1)]:
        for keyword in lang_keywords['negative'][strength]:
            if keyword in text:
                score += weight
                matched.append(f'neg_{strength}:{keyword}')

    # Check neutral keywords (no score impact)
    for keyword in lang_keywords['neutral']:
        if keyword in text:
            matched.append(f'neutral:{keyword}')

    # Clamp score to [-1.0, 1.0]
    score = max(-1.0, min(1.0, score))
    return score, matched

def test_keyword_scorer():
    keywords = load_keywords()

    # Test zh-TW
    zh_text = '台積電宣布 2nm 量產時程提前，外資上調目標價至 2000 元'
    score, matched = score_text(zh_text, 'zh-TW', keywords)
    print(f'zh-TW: score={score:.2f}, matched={matched}')

    # Test ja
    ja_text = 'TSMCが2nmの量産スケジュールを前倒し、外資が目標株価を2000元に引き上げ'
    score, matched = score_text(ja_text, 'ja', keywords)
    print(f'ja: score={score:.2f}, matched={matched}')

    # Test en
    en_text = 'TSMC accelerates 2nm production schedule, foreign investors raise target price to 2000'
    score, matched = score_text(en_text, 'en', keywords)
    print(f'en: score={score:.2f}, matched={matched}')

    # Test auto-detect
    score, matched = score_text(zh_text, None, keywords)
    lang = detect_language(zh_text)
    print(f'auto-detect zh-TW: language={lang}, score={score:.2f}, matched={matched}')

    score, matched = score_text(ja_text, None, keywords)
    lang = detect_language(ja_text)
    print(f'auto-detect ja: language={lang}, score={score:.2f}, matched={matched}')

    # Test neutral
    neutral_text = '台積電公布 7 月營收，年增 5.2% 符合市場預期'
    score, matched = score_text(neutral_text, 'zh-TW', keywords)
    print(f'neutral zh-TW: score={score:.2f}, matched={matched}')

    # Test negative
    negative_text = '台積電南科廠區火災，產線停工估計影響 3% 產能'
    score, matched = score_text(negative_text, 'zh-TW', keywords)
    print(f'negative zh-TW: score={score:.2f}, matched={matched}')

if __name__ == "__main__":
    test_keyword_scorer()