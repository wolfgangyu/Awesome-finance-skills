import pytest
from skills.alphaear-reporter.scripts.report_generator import ReportGenerator
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager
from skills.alphaear-reporter.scripts.utils.llm.default_client import DefaultLLMClient


@pytest.fixture
def mock_signals():
    return [
        {
            "title": "台積電 7 月營收創新高",
            "content": "台積電公布 7 月營收達 NT$ 2,458 億元，年增 31.7%，創歷史新高。主要受惠於 AI 晶片需求強勁。",
            "ticker": "2330.TW",
            "sources": [
                {"title": "台積電公告", "url": "https://www.tsmc.com/news/2330"}
            ]
        },
        {
            "title": "AI 晶片需求推動半導體產業",
            "content": "NVIDIA 最新財報顯示，AI 相關晶片需求持續成長，預計下半年將維持強勁增長。",
            "ticker": "2330.TW",
            "sources": [
                {"title": "NVIDIA 財報", "url": "https://investor.nvidia.com"}
            ]
        },
        {
            "title": "美國半導體法案通過",
            "content": "美國國會通過 CHIPS 法案，將投入 520 億美元支持半導體製造業。",
            "ticker": "NVDA",
            "sources": [
                {"title": "美國國會公告", "url": "https://www.congress.gov"}
            ]
        }
    ]


def test_report_generator_initialization():
    """Test ReportGenerator initialization"""
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    assert generator.market == "tw"
    assert generator.llm_client is None


@pytest.mark.asyncio
async def test_cluster_signals_without_llm(mock_signals):
    """Test _cluster_signals method without LLM"""
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    clusters = await generator._cluster_signals(mock_signals, use_llm=False)

    assert len(clusters) == 2  # 2330.TW 和 NVDA
    assert clusters[0]["ticker"] in ["2330.TW", "NVDA"]
    assert len(clusters[0]["signals"]) == 2  # 2330.TW 有 2 個訊號


@pytest.mark.asyncio
async def test_write_section_without_llm(mock_signals):
    """Test _write_section method without LLM"""
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    # 使用簡化聚類別結果
    cluster = {
        "ticker": "2330.TW",
        "signals": mock_signals[:2],
        "title": "台積電相關訊號"
    }

    section = await generator._write_section(cluster, use_llm=False)

    assert "## 台積電相關訊號" in section
    assert "台積電 7 月營收創新高" in section
    assert "AI 晶片需求推動半導體產業" in section


@pytest.mark.asyncio
async def test_assemble_report_without_llm(mock_signals):
    """Test _assemble_report method without LLM"""
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    # 準備測試章節
    sections = [
        "## 台積電相關訊號\n\n台積電營收創新高...",
        "## 美國半導體政策\n\n美國通過 CHIPS 法案..."
    ]

    report_data = await generator._assemble_report(sections, mock_signals, use_llm=False)

    assert "# 研究報告" in report_data["markdown"]
    assert "台積電相關訊號" in report_data["markdown"]
    assert "美國半導體政策" in report_data["markdown"]
    assert "參考文獻" in report_data["markdown"]


@pytest.mark.asyncio
async def test_generate_report_without_llm(mock_signals):
    """Test generate_report method without LLM"""
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    report = await generator.generate_report(mock_signals, use_llm=False)

    assert "markdown" in report
    assert "json" in report
    assert "line_friendly" in report
    assert "台積電" in report["markdown"]
    assert "台積電" in report["line_friendly"]


@pytest.mark.asyncio
async def test_parse_to_json(mock_signals):
    """Test _parse_to_json method"""
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    # 使用簡單報告進行測試
    markdown = """# 測試報告

## 章節 1
內容 1

## 章節 2
內容 2
"""

    json_report = generator._parse_to_json(markdown)

    assert json_report["title"] == "測試報告"
    assert len(json_report["sections"]) == 2
    assert json_report["sections"][0]["title"] == "章節 1"


@pytest.mark.asyncio
async def test_simplify_for_line(mock_signals):
    """Test _simplify_for_line method"""
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    # 使用簡單報告進行測試
    markdown = """# 測試報告

## 章節 1
內容 1

[來源](https://example.com)
"""

    line_friendly = generator._simplify_for_line(markdown)

    assert "測試報告" in line_friendly
    assert "章節 1" in line_friendly
    assert "來源" in line_friendly
    assert "#" not in line_friendly  # 應移除 Markdown 標題符號


@pytest.mark.asyncio
async def test_market_context_handling(mock_signals):
    """Test market context handling in ReportGenerator"""
    db = DatabaseManager(":memory:")

    # 測試台灣市場
    tw_generator = ReportGenerator(db, market="tw")
    report_tw = await tw_generator.generate_report(mock_signals, use_llm=False)

    # 測試美國市場
    us_generator = ReportGenerator(db, market="us")
    report_us = await us_generator.generate_report(mock_signals, use_llm=False)

    # 兩者應該都包含相同的核心內容，但可能有不同的市場上下文
    assert "台積電" in report_tw["markdown"]
    assert "台積電" in report_us["markdown"]