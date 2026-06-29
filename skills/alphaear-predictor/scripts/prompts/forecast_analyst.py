from typing import List, Dict, Any
from ..schema.models import KLinePoint

def get_forecast_adjustment_instructions(ticker: str, news_context: str, model_forecast: List[KLinePoint]):
    """
    生成 LLM 预测調整指令
    """
    forecast_str = "\n".join([f"- {p.date}: O:{p.open}, C:{p.close}" for p in model_forecast])
    
    return f"""你是一位资深的量化策略分析师。
你的任务是：根据给定的【Kronos 模型预测结果】和【最新的基本面/新闻背景】，对模型预测进行“主观/逻辑調整”。

股票代號: {ticker}

【Kronos 模型原始预测 (OHLC)】:
{forecast_str}

【最新情报背景】:
{news_context}

調整原则:
1. 原始预测是基于歷史的技術面推演。
2. 情报背景中可能套件含【Kronos模型定量修正预测】，这是基于歷史新闻训练的专用模型计算出的量化结果。
3. 如果存在“定量修正预测”，请**高度参考**该数值作為基礎，除非你有非常确凿的逻辑认為该量化模型失效（例如遇到模型未见过的极端黑天鹅）。
4. 你的核心任务是：結合定性分析（新闻及其逻辑）来验证或微调这些数字，并给出合理的解释（Rationale）。
5. 如果没有“定量修正预测”，则你需要根据新闻訊號手动大幅調整趋势。

輸出要求 (严格 JSON 格式):
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
  "rationale": "详细说明調整的逻辑依据，例如：考虑到[事件A]，预期短线將突破压力位..."
}}
```
注意：必须輸出与原始预测相同数量的資料点，且日期一一对应。
"""

def get_forecast_task():
    return "请根据以上背景和模型预测，给出調整后的 K 线資料并说明理由。"
