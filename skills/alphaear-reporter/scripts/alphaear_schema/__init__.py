"""alphaear_schema —— 跨 skill 共享的 Pydantic 資料模型。

此套件為 alphaear-predictor、alphaear-reporter、alphaear-signal-tracker
三個 skill 的 schema source-of-truth，由 ``tools/sync_shared_schema.py``
維護各 skill 內 ``scripts/alphaear_schema/__vendored__.py`` 的版本戳記。
"""

from .models import (
    ClusterContext,
    FilterResult,
    ForecastResult,
    IntentAnalysis,
    InvestmentReport,
    InvestmentSignal,
    KLinePoint,
    ResearchContext,
    ScanContext,
    SignalCluster,
    TransmissionNode,
)
from .isq_template import (
    DEFAULT_ISQ_TEMPLATE,
    ISQDimension,
    ISQDimensionSpec,
    ISQScore,
    ISQTemplate,
    ISQTemplateManager,
    calculate_isq_overall_score,
    get_isq_scoring_prompt,
    get_isq_template,
    isq_template_manager,
)

__version__ = "1.1.0"

__all__ = [
    "ClusterContext",
    "FilterResult",
    "ForecastResult",
    "IntentAnalysis",
    "InvestmentReport",
    "InvestmentSignal",
    "KLinePoint",
    "ResearchContext",
    "ScanContext",
    "SignalCluster",
    "TransmissionNode",
    "DEFAULT_ISQ_TEMPLATE",
    "ISQDimension",
    "ISQDimensionSpec",
    "ISQScore",
    "ISQTemplate",
    "ISQTemplateManager",
    "calculate_isq_overall_score",
    "get_isq_scoring_prompt",
    "get_isq_template",
    "isq_template_manager",
]
