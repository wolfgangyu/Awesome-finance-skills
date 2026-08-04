import pytest
from unittest.mock import patch, MagicMock
from skills.alphaear-reporter.scripts.report_agent import ReportAgent
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager


@pytest.mark.asyncio
async def test_report_agent_initialization():
    """Test ReportAgent initialization"""
    db = DatabaseManager(":memory:")
    agent = ReportAgent(db)

    assert agent.db is not None
    assert agent.generator is not None


@pytest.mark.asyncio
async def test_generate_report_compatibility():
    """Test generate_report method compatibility"""
    db = DatabaseManager(":memory:")
    agent = ReportAgent(db)

    signals = [
        {"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}
    ]

    with patch.object(agent.generator, 'generate_report') as mock_generate:
        mock_generate.return_value = {
            "markdown": "# 測試報告",
            "json": {"title": "測試"},
            "line_friendly": "【測試】"
        }

        result = await agent.generate_report(signals, market="tw")

        assert "markdown" in result
        assert "json" in result
        assert "line_friendly" in result
        assert result["markdown"] == "# 測試報告"
        mock_generate.assert_called_once_with(
            signals=signals,
            use_llm=True,
            user_query=None
        )


@pytest.mark.asyncio
async def test_build_structured_report():
    """Test build_structured_report static method"""
    report_md = "# 測試報告\n\n## 章節 1\n內容 1"
    signals = [{"title": "測試", "content": "內容"}]
    clusters = [{"theme_title": "主題", "signals": []}]

    result = ReportAgent.build_structured_report(report_md, signals, clusters)

    assert result["title"] == "測試報告"
    assert len(result["sections"]) == 1
    assert result["sections"][0]["title"] == "章節 1"


@pytest.mark.asyncio
async def test_market_parameter_handling():
    """Test market parameter handling in ReportAgent"""
    db = DatabaseManager(":memory:")
    agent = ReportAgent(db)

    signals = [{"title": "測試", "content": "內容", "ticker": "AAPL"}]

    with patch.object(agent.generator, 'generate_report') as mock_generate:
        mock_generate.return_value = {
            "markdown": "# US Report",
            "json": {},
            "line_friendly": ""
        }

        # Test US market
        await agent.generate_report(signals, market="us")
        assert agent.generator.market == "us"

        # Test TW market
        await agent.generate_report(signals, market="tw")
        assert agent.generator.market == "tw"