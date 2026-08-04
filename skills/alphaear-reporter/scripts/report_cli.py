#!/usr/bin/env python3
"""
AlphaEar Reporter CLI 介面

供 Hermes Agent 呼叫的標準化 CLI 介面，基於 ReportGenerator 實作。
"""

import argparse
import json
import asyncio
import sys
from typing import List, Dict, Any

from skills.alphaear-reporter.scripts.report_generator import ReportGenerator
from skills.alphaear-reporter.scripts.utils.database_manager import DatabaseManager


async def generate_report_cli(args: argparse.Namespace) -> None:
    """CLI 入口邏輯"""
    try:
        # 初始化
        db = DatabaseManager()
        generator = ReportGenerator(db, market=args.market)

        # 解析輸入
        signals = json.loads(args.signals)
        if not isinstance(signals, list):
            raise ValueError("signals 必須是列表格式")

        # 生成報告
        report = await generator.generate_report(
            signals=signals,
            use_llm=not args.no_llm,
        )

        # 輸出
        if args.output == "markdown":
            print(report["markdown"])
        elif args.output == "json":
            print(json.dumps(report["json"], ensure_ascii=False, indent=2))
        elif args.output == "line":
            print(report["line_friendly"])

    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析錯誤: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 輸入參數錯誤: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 報告生成失敗: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        description="AlphaEar Reporter CLI - 生成金融研究報告",
        epilog="範例: report_cli --signals '[{"title": "台積電營收", "content": "...", "ticker": "2330.TW"}]' --output line"
    )

    # 必要參數
    parser.add_argument(
        "--signals",
        type=str,
        required=True,
        help="輸入訊號的 JSON 字串，格式: [{"title": "...", "content": "...", "ticker": "..."}]"
    )

    # 可選參數
    parser.add_argument(
        "--market",
        type=str,
        default="tw",
        choices=["tw", "us", "both"],
        help="目標市場 (預設: tw) - 可選值: tw (台灣), us (美國), both (台美)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="markdown",
        choices=["markdown", "json", "line"],
        help="輸出格式 (預設: markdown) - 可選值: markdown, json, line"
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="禁用 LLM 驅動邏輯，使用簡化邏輯生成報告"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="啟用除錯模式，輸出詳細日誌"
    )

    args = parser.parse_args()

    if args.debug:
        from loguru import logger
        logger.add(sys.stderr, level="DEBUG")

    asyncio.run(generate_report_cli(args))


if __name__ == "__main__":
    main()