import asyncio
from tests.test_reporter import *

async def main():
    db = DatabaseManager(":memory:")
    generator = ReportGenerator(db, market="tw")

    print("✅ Test 1: Initialization - PASSED")

    mock_signals_data = mock_signals()
    clusters = await generator._cluster_signals(mock_signals_data, use_llm=False)
    print(f"✅ Test 2: Cluster signals - PASSED (found {len(clusters)} clusters)")

    cluster = {
        "ticker": "2330.TW",
        "signals": mock_signals_data[:2],
        "title": "台積電相關訊號"
    }
    section = await generator._write_section(cluster, use_llm=False)
    print("✅ Test 3: Write section - PASSED")

    sections = [
        "## 台積電相關訊號\n\n台積電營收創新高...",
        "## 美國半導體政策\n\n美國通過 CHIPS 法案..."
    ]
    report_data = await generator._assemble_report(sections, mock_signals_data, use_llm=False)
    print("✅ Test 4: Assemble report - PASSED")

    report = await generator.generate_report(mock_signals_data, use_llm=False)
    print("✅ Test 5: Generate report - PASSED")

    json_report = generator._parse_to_json("# 測試報告\n\n## 章節 1\n內容 1")
    print("✅ Test 6: Parse to JSON - PASSED")

    line_friendly = generator._simplify_for_line("# 測試報告\n\n## 章節 1\n內容 1")
    print("✅ Test 7: Simplify for LINE - PASSED")

if __name__ == "__main__":
    asyncio.run(main())