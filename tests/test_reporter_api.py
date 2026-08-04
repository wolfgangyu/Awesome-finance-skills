import pytest
from unittest.mock import patch, MagicMock
from skills.alphaear-reporter.scripts.report_api import ReportAPI


@pytest.mark.asyncio
async def test_generate_report_for_line():
    """Test generate_report_for_line method"""
    signals = [{"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}]

    with patch("skills.alphaear-reporter.scripts.report_api.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 測試報告",
            "line_friendly": "【測試報告】"
        }

        result = await ReportAPI.generate_report_for_line(signals, market="tw")
        assert result == "【測試報告】"
        mock_generator_class.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report_for_liff():
    """Test generate_report_for_liff method"""
    signals = [{"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}]

    with patch("skills.alphaear-reporter.scripts.report_api.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 測試報告\n\n內容"
        }

        result = await ReportAPI.generate_report_for_liff(signals, market="tw")
        assert "<!DOCTYPE html>" in result
        assert "測試報告" in result
        assert "<title>AlphaEar 報告 - TW 市場</title>" in result


@pytest.mark.asyncio
async def test_generate_report_for_hermes():
    """Test generate_report_for_hermes method"""
    signals = [{"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}]

    with patch("skills.alphaear-reporter.scripts.report_api.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 測試",
            "json": {},
            "line_friendly": ""
        }

        result = await ReportAPI.generate_report_for_hermes(signals, market="tw", no_llm=True)
        assert "markdown" in result
        assert "json" in result
        assert "line_friendly" in result
        mock_generator.generate_report.assert_called_once_with(
            signals=signals,
            use_llm=False
        )


@pytest.mark.asyncio
async def test_market_parameter_handling():
    """Test market parameter handling in ReportAPI"""
    signals = [{"title": "測試", "content": "內容", "ticker": "AAPL"}]

    with patch("skills.alphaear-reporter.scripts.report_api.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# US Report",
            "line_friendly": "【US Report】"
        }

        # Test US market
        result = await ReportAPI.generate_report_for_line(signals, market="us")
        assert result == "【US Report】"
        mock_generator_class.assert_called_with(expect.anything(), market="us")

        # Test TW market
        mock_generator_class.reset_mock()
        await ReportAPI.generate_report_for_line(signals, market="tw")
        mock_generator_class.assert_called_with(expect.anything(), market="tw")