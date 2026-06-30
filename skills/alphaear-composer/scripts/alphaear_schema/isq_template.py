"""
ISQ (Investment Signal Quality) 評估框架 Template

統一定義 ISQ 的各個維度、評分標準、和使用方法。
支援預設 template 和自訂 template。
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ISQDimension(str, Enum):
    """ISQ 評估維度"""
    SENTIMENT = "sentiment"              # 情緒/走勢方向
    CONFIDENCE = "confidence"            # 確定性/可信度
    INTENSITY = "intensity"              # 強度/影響量級
    EXPECTATION_GAP = "expectation_gap"  # 預期差/市場認知差
    TIMELINESS = "timeliness"            # 時效性/窗口緊迫度
    TRANSMISSION = "transmission"        # 邏輯傳導清晰度


class ISQDimensionSpec(BaseModel):
    """ISQ 單個維度的定義規範"""
    name: str = Field(..., description="維度名稱")
    key: str = Field(..., description="維度鍵名")
    description: str = Field(..., description="維度描述")
    range_type: str = Field(default="0-1", description="取值範圍 (0-1 或 1-5 等)")
    scale_factor: float = Field(default=1.0, description="顯示時的縮放因子")
    examples: Dict[str, str] = Field(default_factory=dict, description="不同分值的示例解釋")
    visualization_color: Optional[str] = Field(default=None, description="可視化顏色")


class ISQTemplate(BaseModel):
    """ISQ 評估框架 Template"""
    template_id: str = Field(..., description="模板 ID")
    template_name: str = Field(..., description="模板名稱")
    description: str = Field(..., description="模板描述")
    dimensions: Dict[str, ISQDimensionSpec] = Field(..., description="維度定義字典")
    scoring_guide: str = Field(..., description="評分指導說明")
    applicable_scenarios: List[str] = Field(default_factory=list, description="適用場景")
    aggregation_method: str = Field(default="weighted_average", description="聚合方法 (weighted_average, product 等)")
    dimension_weights: Dict[str, float] = Field(default_factory=dict, description="維度權重")


class ISQScore(BaseModel):
    """單個訊號的 ISQ 評分結果"""
    signal_id: str = Field(..., description="訊號 ID")
    template_id: str = Field(..., description="使用的模板 ID")
    scores: Dict[str, float] = Field(..., description="各維度評分")
    overall_score: float = Field(..., description="綜合評分")
    rationale: Dict[str, str] = Field(default_factory=dict, description="各維度評分理由")
    timestamp: str = Field(..., description="評分時間")


DEFAULT_ISQ_TEMPLATE = ISQTemplate(
    template_id="default_isq_v1",
    template_name="標準投資訊號品質評估框架 (ISQ v1.0)",
    description="AlphaEar 預設的 ISQ 評估框架，用於標準化評估投資訊號的品質維度",
    dimensions={
        "sentiment": ISQDimensionSpec(
            name="情緒/走勢",
            key="sentiment",
            description="基礎情緒偏向和市場走勢判斷",
            range_type="-1.0 到 1.0",
            scale_factor=1.0,
            examples={
                "-1.0": "極度悲觀/極度看空",
                "-0.5": "明顯看空",
                "0.0": "中性/沒有明確方向",
                "0.5": "明顯看多",
                "1.0": "極度樂觀/極度看多",
            },
            visualization_color="#ef4444",
        ),
        "confidence": ISQDimensionSpec(
            name="確定性",
            key="confidence",
            description="訊號的可信度和確定性程度",
            range_type="0.0 到 1.0",
            scale_factor=1.0,
            examples={
                "0.0-0.3": "資訊來源不可靠/傳言多/邏輯推導牽強",
                "0.3-0.6": "資訊相對可靠/有一定邏輯/但仍有不確定性",
                "0.6-0.8": "資訊來源權威/邏輯清晰/高度可信",
                "0.8-1.0": "官方確認/資料明確/完全確定",
            },
            visualization_color="#3b82f6",
        ),
        "intensity": ISQDimensionSpec(
            name="強度/影響量級",
            key="intensity",
            description="訊號對相關板塊/個股的潛在影響程度",
            range_type="1 到 5",
            scale_factor=20.0,
            examples={
                "1": "影響微弱，可能被市場忽略",
                "2": "小幅影響，短期可能有波動",
                "3": "中等影響，值得重點關注",
                "4": "強烈影響，可能成為市場焦點",
                "5": "極強影響，市場預期明顯變化",
            },
            visualization_color="#f97316",
        ),
        "expectation_gap": ISQDimensionSpec(
            name="預期差",
            key="expectation_gap",
            description="市場預期與現實之間的差距",
            range_type="0.0 到 1.0",
            scale_factor=1.0,
            examples={
                "0.0-0.2": "市場充分認知，預期差小",
                "0.2-0.5": "市場部分認知，存在一定預期差",
                "0.5-0.8": "市場認知不足，預期差較大，存在博弈空間",
                "0.8-1.0": "市場嚴重低估/高估，巨大預期差",
            },
            visualization_color="#22c55e",
        ),
        "timeliness": ISQDimensionSpec(
            name="時效性",
            key="timeliness",
            description="訊號的時間窗口緊迫度",
            range_type="0.0 到 1.0",
            scale_factor=1.0,
            examples={
                "0.0-0.2": "長期訊號，反應窗口 > 3 月",
                "0.2-0.5": "中期訊號，反應窗口 1-3 月",
                "0.5-0.8": "短期訊號，反應窗口 1 週 - 1 月",
                "0.8-1.0": "超短期訊號，反應窗口 < 1 週（需立即行動）",
            },
            visualization_color="#a855f7",
        ),
    },
    scoring_guide="""
    ### ISQ 評分指導 (Investment Signal Quality)

    ISQ 框架用於多維度評估投資訊號的品質。每個訊號由 5 個維度組成：

    1. **情緒 (Sentiment)**: -1.0 到 1.0，表示看空(-)/中性(0)/看多(+)
    2. **確定性 (Confidence)**: 0.0 到 1.0，數值越高越確定
    3. **強度 (Intensity)**: 1 到 5，數值越高影響越大
    4. **預期差 (Expectation Gap)**: 0.0 到 1.0，市場預期與現實的差距
    5. **時效性 (Timeliness)**: 0.0 到 1.0，反應窗口的緊迫程度

    ### 綜合評分演算法

    綜合評分 = 確定性 × 0.35 + 強度/5 × 0.30 + 預期差 × 0.20 + 時效性 × 0.15

    範圍: 0.0 到 1.0
    - 0.0-0.3: 訊號品質較差，不建議跟進
    - 0.3-0.6: 訊號品質一般，可作參考
    - 0.6-0.8: 訊號品質良好，值得跟進
    - 0.8-1.0: 訊號品質優異，強烈推薦

    ### 評分時的注意事項

    - **不要混淆方向和強度**：情緒可以是看空，但確定性和強度仍可能很高
    - **預期差往往是 Alpha 來源**：高預期差 + 高確定性 = 最佳博弈機會
    - **考慮時間成本**：長期訊號需要更高的確定性才值得跟進
    - **資料為王**：所有評分必須有具體資料支撐
    """,
    applicable_scenarios=[
        "上市公司基本面變化分析",
        "產業政策與監管事件評估",
        "地緣政治與總體經濟影響",
        "技術進步與產業升級",
        "突發事件與應急響應",
    ],
    aggregation_method="weighted_average",
    dimension_weights={
        "confidence": 0.35,
        "intensity": 0.30,
        "expectation_gap": 0.20,
        "timeliness": 0.15,
    },
)


class ISQTemplateManager:
    """ISQ Template 管理器"""

    def __init__(self) -> None:
        self.templates: Dict[str, ISQTemplate] = {
            DEFAULT_ISQ_TEMPLATE.template_id: DEFAULT_ISQ_TEMPLATE,
        }

    def register_template(self, template: ISQTemplate) -> None:
        """註冊新的 template"""
        self.templates[template.template_id] = template

    def register_template_dict(self, template_dict: Dict[str, Any]) -> ISQTemplate:
        """從 dict 註冊範本，回傳實例。"""
        tpl = ISQTemplate(**template_dict)
        self.register_template(tpl)
        return tpl

    def get_template(self, template_id: str) -> ISQTemplate:
        """取得指定 template"""
        if template_id not in self.templates:
            return DEFAULT_ISQ_TEMPLATE
        return self.templates[template_id]

    def list_templates(self) -> List[Dict[str, str]]:
        """列出所有可用 template"""
        return [
            {
                "id": t.template_id,
                "name": t.template_name,
                "description": t.description,
                "dimensions": list(t.dimensions.keys()),
            }
            for t in self.templates.values()
        ]

    def get_dimension(self, template_id: str, dimension_key: str) -> Optional[ISQDimensionSpec]:
        """取得指定 template 的某個維度定義"""
        template = self.get_template(template_id)
        return template.dimensions.get(dimension_key)

    def get_scoring_prompt(self, template_id: str) -> str:
        """取得用於 LLM 的評分 prompt"""
        template = self.get_template(template_id)

        dimensions_desc = "\n".join(
            f"- **{d.name} ({d.key})**\n  範圍: {d.range_type}\n  說明: {d.description}\n  示例: {', '.join(f'{k}={v}' for k, v in list(d.examples.items())[:3])}"
            for d in template.dimensions.values()
        )

        return f"""
### ISQ 評估指導 ({template.template_name})

使用以下 {len(template.dimensions)} 個維度評估訊號品質：

{dimensions_desc}

### 評分標準
{template.scoring_guide}

### 輸出格式 (JSON)
請輸出以下 JSON 格式的評分結果：
{{
  "sentiment": <float>,
  "confidence": <float>,
  "intensity": <int>,
  "expectation_gap": <float>,
  "timeliness": <float>,
  "rationale": {{
    "sentiment": "評分理由",
    "confidence": "評分理由",
    "intensity": "評分理由",
    "expectation_gap": "評分理由",
    "timeliness": "評分理由"
  }}
}}
"""


isq_template_manager = ISQTemplateManager()


def load_templates_from_config(config_path: Optional[str] = None) -> None:
    """從設定目錄載入所有 JSON 範本檔，找不到則跳過，不影響預設範本。
    支援單個 JSON 檔或目錄（目錄下所有 .json 檔）。
    """
    if config_path:
        path = Path(config_path)
    else:
        # 預設目錄：config/isq_templates/
        # __file__ = src/schema/isq_template.py
        path = Path(__file__).resolve().parent.parent.parent / "config"

    if not path.exists():
        return

    if path.is_dir():
        json_files = list(path.glob("*.json"))
    else:
        json_files = [path]

    import json

    for json_file in json_files:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                templates = [data]
            elif isinstance(data, list):
                templates = data
            else:
                continue
            for tpl_dict in templates:
                if not isinstance(tpl_dict, dict):
                    continue
                try:
                    isq_template_manager.register_template_dict(tpl_dict)
                except Exception:
                    continue
        except Exception:
            continue


# 模組載入時自動嘗試載入設定範本
load_templates_from_config()


def get_isq_template(template_id: str = "default_isq_v1") -> ISQTemplate:
    """取得 ISQ template"""
    return isq_template_manager.get_template(template_id)


def get_isq_scoring_prompt(template_id: str = "default_isq_v1") -> str:
    """取得用於 LLM 的 ISQ 評分 prompt"""
    return isq_template_manager.get_scoring_prompt(template_id)


def calculate_isq_overall_score(scores: Dict[str, float], template_id: str = "default_isq_v1") -> float:
    """計算 ISQ 綜合評分"""
    template = get_isq_template(template_id)

    overall = 0.0
    for dim_key, weight in template.dimension_weights.items():
        if dim_key in scores:
            score = scores[dim_key]
            if dim_key == "intensity":
                score = score / 5.0
            overall += score * weight

    return min(1.0, max(0.0, overall))
