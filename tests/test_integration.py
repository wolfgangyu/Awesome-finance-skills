"""
AlphaEar Reporter 整合測試

驗證三種使用場景的整合功能：
1. Claude Code (Agentic Workflow)
2. Hermes Agent (CLI)
3. Polaris 前端 (Python API)
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from skills.alphaear-reporter.scripts.report_generator import ReportGenerator
from skills.alphaear-reporter.scripts.report_cli import generate_report_cli
from skills.alphaear-reporter.scripts.report_api import ReportAPI
from skills.alphaear-reporter.scripts.report_agent import ReportAgent
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager


@pytest.fixture
def mock_signals():
    """測試用訊號資料"""
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
        }
    ]


@pytest.mark.asyncio
async def test_integration_three_scenarios(mock_signals, capsys):
    """整合測試：三種場景使用相同核心邏輯"""
    db = DatabaseManager(":memory:")

    # Mock ReportGenerator 以避免實際 LLM 呼叫
    with patch("skills.alphaear-reporter.scripts.report_generator.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 整合測試報告\n\n## 台積電相關訊號\n台積電營收創新高...",
            "json": {"title": "整合測試報告"},
            "line_friendly": "【整合測試報告】"
        }

        # 1. ReportGenerator 直接使用
        generator = ReportGenerator(db)
        report = await generator.generate_report(mock_signals, use_llm=False)
        assert "整合測試報告" in report["markdown"]

        # 2. CLI 介面（模擬）
        class Args:
            signals = json.dumps(mock_signals)
            market = "tw"
            output = "line"
            no_llm = True
            debug = False

        with patch('builtins.print') as mock_print:
            await generate_report_cli(Args())
            mock_print.assert_called_once_with("【整合測試報告】")

        # 3. Python API
        line_report = await ReportAPI.generate_report_for_line(mock_signals, market="tw")
        assert line_report == "【整合測試報告】"

        liff_report = await ReportAPI.generate_report_for_liff(mock_signals, market="tw")
        assert "<!DOCTYPE html>" in liff_report
        assert "整合測試報告" in liff_report

        # 4. Agentic Workflow
        agent = ReportAgent(db)
        agent_report = await agent.generate_report(mock_signals, market="tw")
        assert "markdown" in agent_report
        assert "json" in agent_report
        assert "line_friendly" in agent_report


@pytest.mark.asyncio
async def test_integration_output_formats(mock_signals):
    """整合測試：輸出格式一致性"""
    db = DatabaseManager(":memory:")

    # Mock ReportGenerator
    with patch("skills.alphaear-reporter.scripts.report_generator.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 測試報告\n\n內容",
            "json": {"title": "測試報告", "sections": []},
            "line_friendly": "【測試報告】"
        }

        # 測試所有場景的輸出格式
        generator = ReportGenerator(db)
        report = await generator.generate_report(mock_signals, use_llm=False)

        # 驗證輸出格式
        assert isinstance(report, dict)
        assert "markdown" in report
        assert "json" in report
        assert "line_friendly" in report
        assert isinstance(report["markdown"], str)
        assert isinstance(report["json"], dict)
        assert isinstance(report["line_friendly"], str)

        # 驗證 LINE 格式特徵
        assert report["line_friendly"].startswith("【")
        assert "#" not in report["line_friendly"]  # 應移除 Markdown 標題符號


@pytest.mark.asyncio
async def test_integration_market_consistency(mock_signals):
    """整合測試：市場參數一致性"""
    db = DatabaseManager(":memory:")

    # Mock ReportGenerator
    with patch("skills.alphaear-reporter.scripts.report_generator.ReportGenerator") as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_report.return_value = {
            "markdown": "# 市場測試報告",
            "json": {},
            "line_friendly": "【市場測試報告】"
        }

        # 測試台灣市場
        generator = ReportGenerator(db, market="tw")
        await generator.generate_report(mock_signals, use_llm=False)
        assert mock_generator.market == "tw"

        # 測試美國市場
        generator = ReportGenerator(db, market="us")
        await generator.generate_report(mock_signals, use_llm=False)
        assert mock_generator.market == "us"

        # 測試 CLI 介面
        class Args:
            signals = json.dumps(mock_signals)
            market = "both"
            output = "markdown"
            no_llm = True
            debug = False

        with patch('builtins.print'):
            await generate_report_cli(Args())
            mock_generator_class.assert_called_with(expect.anything(), market="both")


@pytest.mark.asyncio
async def test_integration_error_handling(mock_signals):
    """整合測試：錯誤處理一致性"""
    db = DatabaseManager(":memory:")

    # 測試空訊號列表
    generator = ReportGenerator(db)
    report = await generator.generate_report([], use_llm=False)
    assert "無內容" in report["markdown"]

    # 測試無效市場參數
    with pytest.raises(ValueError):
        generator = ReportGenerator(db, market="invalid")

    # 測試 CLI 錯誤處理
    class Args:
        signals = "invalid json"
        market = "tw"
        output = "line"
        no_llm = True
        debug = False

    with patch('sys.exit') as mock_exit:
        with patch('builtins.print') as mock_print:
            await generate_report_cli(Args())
            mock_exit.assert_called_once_with(1)
            mock_print.assert_called_once()
            assert "JSON 解析錯誤" in mock_print.call_args[0][0]