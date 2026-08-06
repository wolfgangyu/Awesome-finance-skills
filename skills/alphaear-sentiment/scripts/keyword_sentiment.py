"""多語言關鍵字情緒評分模組。

支援語言：
- English (en)
- Traditional Chinese (zh-TW)
- Japanese (ja)

使用關鍵字字典進行快速情緒評分，無需 LLM。
"""

import re
from typing import Dict, List, Optional
from loguru import logger

# ============================================================================
# 關鍵字字典
# ============================================================================

# 英文關鍵字
EN_KEYWORDS: Dict[str, List[str]] = {
    "bullish": [
        # 正面財務/業績
        "beat", "beats", "exceed", "exceeds", "surpass", "surpasses", "outperform", "outperforms",
        "record high", "record profit", "record revenue", "strong earnings", "strong revenue",
        "profit growth", "revenue growth", "sales growth", "earnings growth",
        "upgrade", "upgraded", "raise target", "raised target", "price target raised",
        "buy rating", "overweight", "outperform rating", "positive outlook",
        "dividend increase", "dividend hike", "share buyback", "stock buyback",
        "guidance raised", "raised guidance", "positive guidance", "upbeat guidance",
        "merger", "acquisition", "takeover", "strategic partnership", "joint venture",
        "new contract", "major order", "breakthrough", "innovation", "patent approved",
        "fda approval", "regulatory approval", "license granted", "milestone reached",
        "expansion", "expanding", "new facility", "new plant", "capacity increase",
        "cost cutting", "cost reduction", "efficiency gain", "margin improvement",
        "margin expansion", "operating leverage", "free cash flow", "fcf growth",
        "bullish", "optimistic", "confident", "strong demand", "robust demand",
        "secular growth", "structural growth", "tailwind", "tailwinds",
        "momentum", "accelerating", "acceleration", "inflection point",
        "turnaround", "restructuring benefits", "synergy", "synergies",
    ],
    "bearish": [
        # 負面財務/業績
        "miss", "misses", "missed", "below estimate", "below estimates", "disappoint",
        "disappoints", "disappointing", "weak earnings", "weak revenue", "weak sales",
        "profit decline", "revenue decline", "sales decline", "earnings decline",
        "downgrade", "downgraded", "cut target", "cut price target", "price target cut",
        "sell rating", "underweight", "underperform rating", "negative outlook",
        "dividend cut", "dividend reduction", "suspend dividend", "no dividend",
        "guidance cut", "lowered guidance", "negative guidance", "weak guidance",
        "guidance withdrawn", "withdraw guidance", "warning", "profit warning",
        "lawsuit", "litigation", "investigation", "probe", "sec investigation",
        "regulatory risk", "regulatory scrutiny", "fine", "penalty", "sanction",
        "recall", "product recall", "safety issue", "quality issue", "defect",
        "layoff", "layoffs", "job cut", "job cuts", "restructuring charge",
        "impairment", "write down", "write off", "goodwill impairment",
        "debt concern", "debt burden", "liquidity risk", "cash burn", "going concern",
        "bearish", "pessimistic", "concerned", "weak demand", "soft demand",
        "headwind", "headwinds", "slowdown", "deceleration", "decelerating",
        "deteriorating", "deterioration", "margin compression", "margin pressure",
        "competition intensifying", "market share loss", "pricing pressure",
        "inventory buildup", "inventory glut", "channel stuffing",
    ],
}

# 繁體中文關鍵字
ZH_TW_KEYWORDS: Dict[str, List[str]] = {
    "bullish": [
        # 正面財務/業績
        "超預期", "優於預期", "超越預期", "勝預期", "表現優於", "業績優於",
        "創新高", "歷史新高", "獲利創高", "營收創高", "盈餘創高",
        "獲利成長", "營收成長", "營收增加", "獲利大增", "營運成長",
        "上調", "調高", "目標價上調", "目標價調高", "評等上調",
        "買進", "增碼", "優於大盤", "看好", "正面展望", "樂觀展望",
        "現金增資", "股票回購", "庫藏股", "發放股利", "增加股利", "股利上調",
        "財測上調", "財測調高", "正面財測", "樂觀財測", "展望正向",
        "併購", "收購", "策略聯盟", "合資", "合作備忘錄",
        "新訂單", "大單", "重大訂單", "突破", "創新", "專利通過",
        "核准", "許可通過", "里程碑", "達成里程碑",
        "擴產", "擴廠", "新廠", "產能擴充", "產能增加",
        "降低成本", "成本下降", "效率提升", "毛利改善", "毛利擴大",
        "營業槓桿", "自由現金流", "現金流改善",
        "看多", "樂觀", "信心", "強勁需求", "旺盛需求",
        "長期成長", "結構性成長", "順風", "利多",
        "動能", "加速", "轉折點", "趨勢反轉",
        "扭虧為盈", "重組效益", "協同效應",
        "漲停", "大漲", "飆漲", "強勢", "多頭",
        "法人買超", "外資買超", "投信買超", "自營商買超",
        "月增率", "年增率", "雙位數成長", "歷史同期新高",
        "每股盈餘", "eps成長", "eps優於預期", "獲利能力改善",
        "殖利率", "高股利", "配息", "現金殖利率",
    ],
    "bearish": [
        # 負面財務/業績
        "不及預期", "遜於預期", "低於預期", "表現遜於", "業績遜於",
        "創新低", "獲利衰退", "營收衰退", "營收減少", "獲利大減", "營運下滑",
        "下調", "調降", "目標價下調", "目標價調降", "評等下調",
        "賣出", "減碼", "遜於大盤", "看壞", "負面展望", "悲觀展望",
        "減資", "停止配息", "減少股利", "股利下調", "不配息",
        "財測下調", "財測調降", "負面財測", "悲觀財測", "展望負面",
        "財測撤回", "撤回財測", "獲利預警", "獲利警訊",
        "訴訟", "法律糾紛", "調查", "偵查", "監管調查",
        "監管風險", "監管審查", "罰款", "處罰", "制裁",
        "召回", "產品召回", "安全疑慮", "品質問題", "缺陷",
        "裁員", "大規模裁員", "減員", "重組費用", "重組支出",
        "減損", "資產減損", "商譽減損", "帳面價值減損",
        "債務疑慮", "債務負擔", "流動性風險", "燒錢", "持續經營疑慮",
        "看空", "悲觀", "擔憂", "需求疲軟", "需求放緩",
        "逆風", "利空", "放緩", "減速", "惡化", "惡化中",
        "毛利壓縮", "毛利承壓", "獲利能力下降",
        "競爭加劇", "市佔率流失", "價格壓力", "價格戰",
        "庫存積壓", "庫存過高", "渠道庫存高",
        "跌停", "大跌", "重挫", "弱勢", "空頭",
        "法人賣超", "外資賣超", "投信賣超", "自營商賣超",
        "月減率", "年減率", "衰退", "同期比較下降",
        "每股虧損", "eps衰退", "eps遜於預期", "獲利能力惡化",
        "除息", "除權", "股價暴跌", "市值蒸發",
    ],
}

# 日文關鍵字
JA_KEYWORDS: Dict[str, List[str]] = {
    "bullish": [
        # 正面財務/業績
        "上方修正", "上方修正", "業績上方修正", "予想上回り", "予想を上回る",
        "過去最高", "最高益", "最高売上", "過去最高益", "過去最高売上",
        "増益", "増収", "売上高増加", "利益増加", "業績好調",
        "目標株価引き上げ", "目標株価上方修正", "レーティング引き上げ",
        "買い推奨", "オーバーウェイト", "アウトパフォーム", "強気見通し",
        "配当増配", "増配", "自社株買い", "自己株取得",
        "業績予想上方修正", "上方修正", "強気業績予想", "ポジティブ見通し",
        "M&A", "買収", "戦略的提携", "ジョイントベンチャー", "業務提携",
        "大型受注", "大口受注", "ブレークスルー", "革新", "特許取得",
        "承認取得", "認可取得", "マイルストーン達成",
        "増産", "新工場", "生産能力拡大", "設備投資拡大",
        "コスト削減", "コスト低減", "効率改善", "利益率改善", "マージン拡大",
        "営業レバレッジ", "フリーキャッシュフロー", "FCF増加",
        "強気", "楽観的", "自信", "堅調な需要", "旺盛な需要",
        "構造的成長", "セキュラーグロース", "追い風", "追い風材料",
        "モメンタム", "加速", "転換点", "インフレクションポイント",
        "業績回復", "ターンアラウンド", "再編効果", "シナジー効果",
        "ストップ高", "大幅高", "急騰", "強気相場", "買い優勢",
        "機関投資家買い", "外国人買い", "信託銀行買い",
        "月次増", "前年比増", "二桁成長", "過去最高水準",
        "一株利益増加", "EPS増加", "EPS上方修正", "収益力改善",
        "配当利回り", "高配当", "配当金", "現金配当利回り",
    ],
    "bearish": [
        # 負面財務/業績
        "下方修正", "業績下方修正", "予想下回り", "予想を下回る", "失望",
        "過去最低", "減益", "減収", "売上高減少", "利益減少", "業績不振",
        "目標株価引き下げ", "目標株価下方修正", "レーティング引き下げ",
        "売り推奨", "アンダーウェイト", "アンダーパフォーム", "弱気見通し",
        "配当減配", "減配", "無配", "配当見送り",
        "業績予想下方修正", "下方修正", "弱気業績予想", "ネガティブ見通し",
        "業績予想撤回", "撤回", "業績警告", "減益警告",
        "訴訟", "法的紛争", "調査", "捜査", "当局調査",
        "規制リスク", "規制当局の審査", "罰金", "制裁金", "制裁",
        "リコール", "製品リコール", "安全性懸念", "品質問題", "欠陥",
        "リストラ", "大量解雇", "人員削減", "構造改革費用", "リストラ費用",
        "減損", "資産減損", "のれん減損", "帳簿価値減損",
        "債務懸念", "債務負担", "流動性リスク", "キャッシュバーン", "継続企業懸念",
        "弱気", "悲観的", "懸念", "需要軟調", "需要鈍化",
        "逆風", "逆風材料", "減速", "鈍化", "悪化", "悪化傾向",
        "利益率圧迫", "マージン圧迫", "収益力低下",
        "競争激化", "シェア低下", "価格圧力", "価格競争",
        "在庫積み上がり", "在庫過剰", "チャネル在庫高",
        "ストップ安", "大幅安", "暴落", "弱気相場", "売り優勢",
        "機関投資家売り", "外国人売り", "信託銀行売り",
        "月次減", "前年比減", "減退", "前年同期比減少",
        "一株損失", "EPS減少", "EPS下方修正", "収益力悪化",
        "除配当", "除権", "株価暴落", "時価総額蒸発",
    ],
}

# ============================================================================
# 語言檢測與評分邏輯
# ============================================================================

LANGUAGE_KEYWORDS_MAP = {
    "en": EN_KEYWORDS,
    "zh-TW": ZH_TW_KEYWORDS,
    "zh": ZH_TW_KEYWORDS,  # fallback
    "ja": JA_KEYWORDS,
    "japanese": JA_KEYWORDS,
    "unknown": EN_KEYWORDS,  # default fallback
}

def detect_language(text: str, meta_language: Optional[str] = None) -> str:
    """檢測文本語言。

    優先使用 meta_language，否則基於字符特徵判斷。
    """
    if meta_language and meta_language in LANGUAGE_KEYWORDS_MAP:
        return meta_language

    if not text:
        return "unknown"

    # 統計字符類型
    ja_chars = len(re.findall(r'[぀-ゟ゠-ヿ一-鿿]', text))
    zh_chars = len(re.findall(r'[一-鿿]', text))
    en_chars = len(re.findall(r'[A-Za-z]', text))

    total = ja_chars + zh_chars + en_chars
    if total == 0:
        return "unknown"

    # 日文特有：平假名/片假名
    if ja_chars > 0 and (ja_chars / total) > 0.15:
        return "ja"

    # 中文：漢字佔比高
    if zh_chars > 0 and (zh_chars / total) > 0.3:
        # 簡體/繁體無法完全區分，預設繁體
        return "zh-TW"

    # 英文佔比高
    if en_chars / total > 0.5:
        return "en"

    return "unknown"


def calculate_keyword_sentiment(
    text: str,
    language: Optional[str] = None,
    meta_language: Optional[str] = None,
) -> float:
    """基於關鍵字計算情緒分數 (-1.0 到 1.0)。

    Args:
        text: 要分析的文本（標題 + 內容）
        language: 強制指定語言 (en/zh-TW/ja)
        meta_language: 來自新聞元數據的語言提示

    Returns:
        情緒分數：-1.0 (極度負面) 到 1.0 (極度正面)，0.0 為中性
    """
    if not text or not text.strip():
        return 0.0

    # 確定語言
    lang = language or detect_language(text, meta_language)
    keywords = LANGUAGE_KEYWORDS_MAP.get(lang, EN_KEYWORDS)

    text_lower = text.lower()

    # 計算正面/負面關鍵字命中數
    bullish_hits = 0
    bearish_hits = 0

    # 為了避免重複計算同一關鍵字多次，使用集合
    matched_bullish = set()
    matched_bearish = set()

    for kw in keywords["bullish"]:
        # 使用詞邊界匹配（中日文不需要詞邊界）
        if lang in ("zh-TW", "ja", "zh"):
            if kw in text:
                matched_bullish.add(kw)
        else:
            # 英文使用詞邊界
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, text_lower):
                matched_bullish.add(kw)

    for kw in keywords["bearish"]:
        if lang in ("zh-TW", "ja", "zh"):
            if kw in text:
                matched_bearish.add(kw)
        else:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, text_lower):
                matched_bearish.add(kw)

    bullish_hits = len(matched_bullish)
    bearish_hits = len(matched_bearish)

    # 計算分數
    total_hits = bullish_hits + bearish_hits
    if total_hits == 0:
        return 0.0

    # 基礎分數：正面比例 - 負面比例
    raw_score = (bullish_hits - bearish_hits) / total_hits

    # 根據命中總數調整置信度（命中越多越可信）
    confidence_factor = min(1.0, total_hits / 5.0)  # 5個關鍵字達到滿置信度

    final_score = raw_score * confidence_factor

    # 限制範圍
    final_score = max(-1.0, min(1.0, final_score))

    logger.debug(
        f"Keyword sentiment: lang={lang}, bullish={bullish_hits}({matched_bullish}), "
        f"bearish={bearish_hits}({matched_bearish}), raw={raw_score:.2f}, "
        f"confidence={confidence_factor:.2f}, final={final_score:.2f}"
    )

    return round(final_score, 2)


def batch_score_news(
    news_items: List[Dict],
    default_language: Optional[str] = None,
) -> List[Dict]:
    """批量為新聞列表評分。

    Args:
        news_items: 新聞字典列表，每個需包含 title, content, meta_data
        default_language: 默認語言

    Returns:
        添加了 sentiment_score 和 sentiment_keywords_matched 的新聞列表
    """
    scored_items = []

    for item in news_items:
        title = item.get("title", "") or ""
        content = item.get("content", "") or ""
        meta = item.get("meta_data", {}) or {}

        # 合併標題和內容
        full_text = f"{title} {content}"

        # 從 meta_data 獲取語言
        meta_lang = meta.get("language") if isinstance(meta, dict) else None

        score = calculate_keyword_sentiment(
            full_text,
            language=default_language,
            meta_language=meta_lang,
        )

        # 創建新項目（不修改原對象）
        scored_item = item.copy()
        scored_item["sentiment_score"] = score
        scored_item["sentiment_method"] = "keyword"

        scored_items.append(scored_item)

    return scored_items


# ============================================================================
# 測試用主程序
# ============================================================================

if __name__ == "__main__":
    # 簡單測試
    test_cases = [
        # 英文
        ("Apple beats earnings estimates, raises guidance for next quarter", "en"),
        ("Company misses revenue estimates, cuts guidance, announces layoffs", "en"),
        # 繁體中文
        ("台積電獲利超預期，上調財測看好 AI 需求", "zh-TW"),
        ("某公司獲利大減，下調財測並宣布大規模裁員", "zh-TW"),
        # 日文
        ("トヨタ、業績上方修正で過去最高益を更新", "ja"),
        ("大手企業、減益見通しで大量リストラを発表", "ja"),
        # 無關鍵字
        ("今日股市收盤報告", "zh-TW"),
        ("Market closes mixed today", "en"),
    ]

    print("=== 關鍵字情緒評分測試 ===\n")
    for text, lang in test_cases:
        score = calculate_keyword_sentiment(text, language=lang)
        print(f"[{lang}] {text[:50]}...")
        print(f"  Score: {score:.2f}\n")