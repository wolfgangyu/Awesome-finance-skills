from typing import List, Dict, Any
from ..schema.models import KLinePoint
from ._market_prompts import HUMANIZE_ZH_INSTRUCTION

def get_forecast_adjustment_instructions(ticker: str, news_context: str, model_forecast: List[KLinePoint]):
    """
    生成 LLM 預測調整指令
    """
    forecast_str = "\n".join([f"- {p.date}: O:{p.open}, C:{p.close}" for p in model_forecast])

    return f"""你是一位資深的量化策略分析師。
你的任務是：根據給定的【Kronos 模型預測結果】和【最新的基本面/新聞背景】，對模型預測進行「主觀/邏輯調整」。

股票代號: {ticker}

【Kronos 模型原始預測 (OHLC)】:
{forecast_str}

【最新情報背景】:
{news_context}

調整原則:
1. 原始預測是基於歷史的技術面推演。
2. 情報背景中可能套件含【Kronos模型定量修正預測】，這是基於歷史新聞訓練的專用模型計算出的量化結果。
3. 如果存在「定量修正預測」，請**高度參考**該數值作為基礎，除非你有非常確鑿的邏輯認為該量化模型失效（例如遇到模型未見過的極端黑天鵝）。
4. 你的核心任務是：結合定性分析（新聞及其邏輯）來驗證或微調這些數字，並給出合理的解釋（Rationale）。
5. 如果沒有「定量修正預測」，則你需要根據新聞信號手動大幅調整趨勢。

輸出要求 (嚴格 JSON 格式):
```json
{{
  "adjusted_forecast": [
    {{
      "date": "YYYY-MM-DD",
      "open": float,
      "high": float,
      "low": float,
      "close": float,
      "volume": float
    }},
    ...
  ],
  "rationale": "詳細說明調整的邏輯依據，例如：考慮到[事件A]，預期短線將突破壓力位..."
}}
```
注意：必須輸出與原始預測相同數量的資料點，且日期一一對應。
{HUMANIZE_ZH_INSTRUCTION}
"""

def get_forecast_task():
    return "請根據以上背景和模型預測，給出調整後的 K 線資料並說明理由。"
