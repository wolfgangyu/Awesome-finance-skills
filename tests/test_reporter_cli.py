import pytest
import json
from unittest.mock import patch, MagicMock
from skills.alphaear-reporter.scripts.report_cli import generate_report_cli


@pytest.mark.asyncio
async def test_cli_basic_functionality():
    """Test CLI basic functionality"""
    # 準備測試參數
    args = MagicMock()
    args.signals = json.dumps([
        {"title": "測試訊號", "content": "測試內容", "ticker": "2330.TW"}
    ])
    args.market = "tw"
    args.output = "line"
    args.no_llm = True
    args.debug = False

    # Mock ReportGenerator
    with patch("skills.alphaear-reporter.scripts.report_cli.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 測試報告",
            "json": {"title": "測試報告"},
            "line_friendly": "【測試報告】"
        }

        # 執行並捕獲輸出
        with patch('builtins.print') as mock_print:
            await generate_report_cli(args)
            mock_print.assert_called_once_with("【測試報告】")


@pytest.mark.asyncio
async def test_cli_json_output():
    """Test CLI JSON output"""
    args = MagicMock()
    args.signals = json.dumps([{"title": "測試", "content": "內容", "ticker": "2330.TW"}])
    args.market = "tw"
    args.output = "json"
    args.no_llm = True

    with patch("skills.alphaear-reporter.scripts.report_cli.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 測試",
            "json": {"title": "測試報告"},
            "line_friendly": "【測試】"
        }

        with patch('builtins.print') as mock_print:
            await generate_report_cli(args)
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            assert "測試報告" in output


@pytest.mark.asyncio
async def test_cli_error_handling():
    """Test CLI error handling"""
    args = MagicMock()
    args.signals = "invalid json"
    args.market = "tw"
    args.output = "line"
    args.no_llm = True

    with patch('sys.exit') as mock_exit:
        with patch('builtins.print') as mock_print:
            await generate_report_cli(args)
            mock_exit.assert_called_once_with(1)
            mock_print.assert_called_once()
            assert "JSON 解析錯誤" in mock_print.call_args[0][0]


@pytest.mark.asyncio
async def test_cli_market_parameter():
    """Test CLI market parameter handling"""
    args = MagicMock()
    args.signals = json.dumps([{"title": "測試", "content": "內容", "ticker": "AAPL"}])
    args.market = "us"
    args.output = "markdown"
    args.no_llm = True

    with patch("skills.alphaear-reporter.scripts.report_cli.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# US Report",
            "json": {},
            "line_friendly": ""
        }

        with patch('builtins.print') as mock_print:
            await generate_report_cli(args)
            mock_print.assert_called_once_with("# US Report")
            mock_generator_class.assert_called_once_with(expect.anything(), market="us")