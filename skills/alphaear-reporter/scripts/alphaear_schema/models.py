"""alphaear_schema.models —— ISQ 投資訊號資料模型（single source of truth）。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TransmissionNode(BaseModel):
    node_name: str = Field(..., description="產業鏈節點名稱")
    impact_type: str = Field(..., description="利好/利空/中性")
    logic: str = Field(..., description="該節點的傳導邏輯")


class IntentAnalysis(BaseModel):
    keywords: List[str] = Field(..., description="核心實體、事件或概念關鍵詞")
    search_queries: List[str] = Field(..., description="優化後的搜尋引擎查詢詞")
    is_specific_event: bool = Field(..., description="是否查詢特定突發事件")
    time_range: str = Field(..., description="時間範圍 (recent/all/specific_date)")
    intent_summary: str = Field(..., description="一句話意圖描述")


class FilterResult(BaseModel):
    """LLM 篩選結果 - 快速判斷是否有有效訊號"""
    has_valid_signals: bool = Field(..., description="列表中是否包含有效的金融訊號")
    selected_ids: List[int] = Field(default_factory=list, description="篩選出的有效訊號 ID 列表")
    themes: List[str] = Field(default_factory=list, description="訊號涉及的主題")
    reason: Optional[str] = Field(default=None, description="如果無有效訊號，說明原因")


class InvestmentSignal(BaseModel):
    # 核心 metadata
    signal_id: str = Field(default="unknown_sig", description="唯一訊號 ID")
    title: str = Field(..., description="訊號標題")
    summary: str = Field(default="暫無摘要分析", description="100 字核心觀點快報")
    reasoning: str = Field(default="", description="詳細的推演邏輯和理由")

    # 邏輯傳導 (ISQ Key 1)
    transmission_chain: List[TransmissionNode] = Field(default_factory=list, description="產業鏈傳導邏輯鏈條")

    # 訊號品質 (ISQ Key 2) - 來自 isq_template.DEFAULT_ISQ_TEMPLATE
    # 參考: src/schema/isq_template.py 的 DEFAULT_ISQ_TEMPLATE 定義
    sentiment_score: float = Field(default=0.0, description="[ISQ] 情緒/走勢 (-1.0=極度看空 ~ 0.0=中性 ~ 1.0=極度看多)")
    confidence: float = Field(default=0.5, description="[ISQ] 確定性 (0.0=不可信 ~ 1.0=完全確定)")
    intensity: int = Field(default=3, description="[ISQ] 強度/影響量級 (1=微弱 ~ 5=極強)")
    expectation_gap: float = Field(default=0.5, description="[ISQ] 預期差/博弈空間 (0.0=充分定價 ~ 1.0=巨大預期差)")
    timeliness: float = Field(default=0.8, description="[ISQ] 時效性 (0.0=長期 ~ 1.0=超短期)")

    # 預測與博弈 (ISQ Key 3)
    expected_horizon: str = Field(default="T+N", description="預期的反應時窗 (如: T+0, T+3, Long-term)")
    price_in_status: str = Field(default="未知", description="市場預期消化程度 (未定價/部分定價/充分定價)")

    # 關聯實體
    impact_tickers: List[Dict[str, Any]] = Field(default_factory=list, description="受影響的代號列表及其權重")
    industry_tags: List[str] = Field(default_factory=list, description="關聯行業標籤")

    # 溯源
    sources: List[Dict[str, str]] = Field(default_factory=list, description="來源詳情 (包含 title, url, source_name)")


class ResearchContext(BaseModel):
    """研究員搜集的背景資訊結構"""
    raw_signal: str = Field(..., description="原始訊號內容")
    tickers_found: List[Dict[str, Any]] = Field(default_factory=list, description="找到的相關標的及其基本面/股價資訊")
    industry_background: str = Field(..., description="行業背景及產業鏈現狀")
    latest_developments: List[str] = Field(default_factory=list, description="相關事件的最新進展")
    key_risks: List[str] = Field(default_factory=list, description="潛在風險點")
    search_results_summary: str = Field(..., description="搜尋結果的綜合摘要")


class ScanContext(BaseModel):
    """掃描員搜集的原始資料結構"""
    hot_topics: List[str] = Field(..., description="當前市場熱點話題")
    news_summaries: List[Dict[str, Any]] = Field(..., description="關鍵新聞摘要列表")
    market_data: Dict[str, Any] = Field(default_factory=dict, description="相關的市場行情資料")
    sentiment_overview: str = Field(..., description="整體市場情緒概覽")
    raw_data_summary: str = Field(..., description="原始資料的綜合摘要")


class SignalCluster(BaseModel):
    theme_title: str = Field(..., description="主題名稱")
    signal_ids: List[int] = Field(..., description="包含的訊號 ID 列表")
    rationale: str = Field(..., description="聚類理由")


class ClusterContext(BaseModel):
    """訊號聚類結果結構"""
    clusters: List[SignalCluster] = Field(..., description="聚類列表")


class KLinePoint(BaseModel):
    date: str = Field(..., description="日期")
    open: float = Field(..., description="開盤價")
    high: float = Field(..., description="最高價")
    low: float = Field(..., description="最低價")
    close: float = Field(..., description="收盤價")
    volume: float = Field(..., description="成交量")


class ForecastResult(BaseModel):
    ticker: str = Field(..., description="股票代號")
    base_forecast: List[KLinePoint] = Field(default_factory=list, description="Kronos 模型原始預測")
    adjusted_forecast: List[KLinePoint] = Field(default_factory=list, description="LLM 調整後的預測")
    rationale: str = Field(default="", description="預測調整理由及邏輯說明")
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), description="生成時間")


class InvestmentReport(BaseModel):
    overall_sentiment: str = Field(..., description="整體市場情緒評價")
    market_entropy: float = Field(..., description="市場分歧度 (0-1, 1代表極高分歧)")
    signals: List[InvestmentSignal] = Field(..., description="深度解析的投資訊號列表")
    forecasts: List[ForecastResult] = Field(default_factory=list, description="相關標的的預測結果")
    timestamp: str = Field(..., description="報告生成時間")
    meta_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="其他 metadata")
