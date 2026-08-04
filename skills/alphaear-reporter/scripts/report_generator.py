"""
ReportGenerator 核心邏輯實作

將現有的 Agentic Workflow 轉換為可程式化呼叫的核心元件。
此類別將被 CLI、Python API 和 Agentic Workflow 三種進入點共用。

架構設計：
- 簡化邏輯（無 LLM）：快速聚類別和報告生成
- LLM 驅動邏輯：深度分析和智能撰寫
- 統一輸出格式：Markdown、JSON、LINE 友好格式
"""

from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import json
import re

from .utils.database_manager import DatabaseManager
from .utils.llm.base_client import LLMClient
from .prompts.report_agent import (
    format_signal_for_report,
    get_cluster_planner_instructions,
    get_report_writer_instructions,
    get_final_assembly_instructions,
)


class ReportGenerator:
    """
    ReportGenerator 核心類別 - 生成金融研究報告

    Attributes:
        db: DatabaseManager 實例
        llm_client: LLMClient 實例（可選）
        market: 市場類型（預設: "tw"）
    """

    def __init__(
        self,
        db: DatabaseManager,
        llm_client: Optional[LLMClient] = None,
        market: str = "tw",
    ):
        """
        初始化 ReportGenerator

        Args:
            db: DatabaseManager 實例
            llm_client: LLMClient 實例（可選，用於 LLM 驅動邏輯）
            market: 市場類型代碼，例如 "tw" (台灣)、"us" (美國)
        """
        self.db = db
        self.llm_client = llm_client
        self.market = market.lower()

        logger.info(f"📊 ReportGenerator 初始化完成 - 市場: {self.market}, LLM 客戶端: {llm_client is not None}")

    async def generate_report(
        self,
        signals: List[Dict[str, Any]],
        use_llm: bool = True,
        user_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成完整研究報告

        Args:
            signals: 投資訊號列表
            use_llm: 是否使用 LLM 驅動邏輯（預設: True）
            user_query: 使用者查詢（可選，用於指導報告方向）

        Returns:
            報告字典，包含:
            - "markdown": 完整 Markdown 格式報告
            - "json": 結構化 JSON 報告
            - "line_friendly": LINE 官方帳號友好格式
        """
        logger.info(f"✨ 開始生成報告 - 訊號數量: {len(signals)}, 使用 LLM: {use_llm}")

        try:
            # 階段 1: 聚類別訊號
            clusters = await self._cluster_signals(signals, use_llm=use_llm, user_query=user_query)
            logger.info(f"📦 訊號聚類別完成 - 產生 {len(clusters)} 個主題簇")

            # 階段 2: 撰寫各章節
            sections = []
            for cluster in clusters:
                section = await self._write_section(cluster, use_llm=use_llm, user_query=user_query)
                sections.append(section)
            logger.info(f"📝 章節撰寫完成 - {len(sections)} 個章節")

            # 階段 3: 組裝完整報告
            report_data = await self._assemble_report(sections, signals, use_llm=use_llm, user_query=user_query)

            # 階段 4: 輔助格式輸出
            json_report = self._parse_to_json(report_data["markdown"])
            line_friendly = self._simplify_for_line(report_data["markdown"])

            result = {
                "markdown": report_data["markdown"],
                "json": json_report,
                "line_friendly": line_friendly,
            }

            logger.success("🎉 報告生成成功完成")
            return result

        except Exception as e:
            logger.error(f"❌ 報告生成失敗: {e}")
            raise

    async def _cluster_signals(
        self,
        signals: List[Dict[str, Any]],
        use_llm: bool = True,
        user_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        將訊號聚類別成主題簇

        實作兩種模式：
        1. 簡化邏輯（無 LLM）：按 ticker 或產業聚類別
        2. LLM 驅動邏輯：智能主題聚類別

        Args:
            signals: 原始訊號列表
            use_llm: 是否使用 LLM 驅動邏輯
            user_query: 使用者查詢（可選）

        Returns:
            聚類別後的主題簇列表
        """
        if not signals:
            logger.warning("⚠️ 空訊號列表 - 返回空聚類別")
            return []

        if not use_llm or not self.llm_client:
            # --- 簡化邏輯：按 ticker 聚類別 ---
            logger.info("🔍 使用簡化邏輯聚類別訊號（按 ticker）")

            clusters = {}
            for signal in signals:
                ticker = signal.get("ticker", "unknown")
                if ticker not in clusters:
                    clusters[ticker] = {
                        "ticker": ticker,
                        "signals": [],
                        "title": f"{ticker} 相關訊號",
                    }
                clusters[ticker]["signals"].append(signal)

            result = list(clusters.values())
            logger.info(f"📊 簡化聚類別完成 - {len(result)} 個主題簇")
            return result

        # --- LLM 驅動邏輯：智能主題聚類別 ---
        logger.info("🤖 使用 LLM 驅動邏輯聚類別訊號")

        try:
            # 準備訊號文本用於 LLM 處理
            signals_text = "\n\n".join([
                format_signal_for_report(signal, idx + 1)
                for idx, signal in enumerate(signals)
            ])

            # 生成聚類別提示
            prompt = get_cluster_planner_instructions(signals_text, user_query=user_query)

            logger.debug(f"📝 LLM 聚類別提示長度: {len(prompt)} 字元")

            # 呼叫 LLM
            response = await self.llm_client.generate(
                prompt=prompt,
                json_mode=True,
                temperature=0.3,  # 低隨機性，確保穩定聚類別
                max_tokens=2048,
            )

            logger.debug(f"🤖 LLM 聚類別響應: {response[:200]}...")

            # 解析 JSON 響應
            clusters_data = json.loads(response)

            # 轉換為標準格式
            result = []
            for cluster_info in clusters_data.get("clusters", []):
                cluster = {
                    "theme_title": cluster_info.get("theme_title", "未命名主題"),
                    "signals": [],
                    "rationale": cluster_info.get("rationale", ""),
                }

                # 找到對應的訊號
                signal_ids = cluster_info.get("signal_ids", [])
                for signal_id in signal_ids:
                    if 0 <= signal_id - 1 < len(signals):
                        cluster["signals"].append(signals[signal_id - 1])

                result.append(cluster)

            logger.success(f"🤖 LLM 聚類別完成 - {len(result)} 個主題簇")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析失敗: {e}")
            # 回退到簡化邏輯
            logger.warning("🔄 回退到簡化邏輯聚類別")
            return self._cluster_signals(signals, use_llm=False, user_query=user_query)
        except Exception as e:
            logger.error(f"❌ LLM 聚類別失敗: {e}")
            # 回退到簡化邏輯
            logger.warning("🔄 回退到簡化邏輯聚類別")
            return self._cluster_signals(signals, use_llm=False, user_query=user_query)

    async def _write_section(
        self,
        cluster: Dict[str, Any],
        use_llm: bool = True,
        user_query: Optional[str] = None,
    ) -> str:
        """
        撰寫單個章節內容

        Args:
            cluster: 主題簇字典
            use_llm: 是否使用 LLM 驅動邏輯
            user_query: 使用者查詢（可選）

        Returns:
            章節 Markdown 內容
        """
        theme_title = cluster.get("theme_title", "未命名主題")
        signals = cluster.get("signals", [])

        if not signals:
            logger.warning(f"⚠️ 主題 '{theme_title}' 沒有訊號 - 返回空章節")
            return f"## {theme_title}\n\n（無相關訊號）\n"

        if not use_llm or not self.llm_client:
            # --- 簡化邏輯：基本格式化 ---
            logger.info(f"📝 使用簡化邏輯撰寫章節: {theme_title}")

            # 準備訊號文本
            signals_text = "\n\n".join([
                f"### 訊號 {idx + 1}\n\n{signal.get('title', '無標題')}\n\n{signal.get('content', '')}"
                for idx, signal in enumerate(signals)
            ])

            section_content = f"""## {theme_title}

### 訊號彙整

{signals_text}

### 分析總結

基於以上 {len(signals)} 個相關訊號進行分析。
"""

            logger.info(f"✅ 簡化章節撰寫完成: {theme_title}")
            return section_content

        # --- LLM 驅動邏輯：深度分析撰寫 ---
        logger.info(f"🤖 使用 LLM 撰寫章節: {theme_title}")

        try:
            # 準備訊號文本
            signals_text = "\n\n".join([
                format_signal_for_report(signal, idx + 1)
                for idx, signal in enumerate(signals)
            ])

            # 生成撰寫提示
            prompt = get_report_writer_instructions(
                theme_title=theme_title,
                signal_cluster_text=signals_text,
                signal_indices=list(range(1, len(signals) + 1)),
                user_query=user_query,
                market=self.market,
            )

            logger.debug(f"📝 LLM 撰寫提示長度: {len(prompt)} 字元")

            # 呼叫 LLM
            response = await self.llm_client.generate(
                prompt=prompt,
                json_mode=False,
                temperature=0.7,
                max_tokens=4096,
            )

            logger.debug(f"🤖 LLM 撰寫響應長度: {len(response)} 字元")

            # 基本格式驗證
            if not response.strip():
                logger.warning("⚠️ LLM 返回空響應 - 使用簡化邏輯")
                return self._write_section(cluster, use_llm=False, user_query=user_query)

            # 確保標題格式正確
            if not response.strip().startswith(f"## {theme_title}"):
                response = f"## {theme_title}\n\n" + response

            logger.success(f"✅ LLM 章節撰寫完成: {theme_title}")
            return response

        except Exception as e:
            logger.error(f"❌ LLM 章節撰寫失敗: {e}")
            # 回退到簡化邏輯
            logger.warning("🔄 回退到簡化邏輯撰寫")
            return self._write_section(cluster, use_llm=False, user_query=user_query)

    async def _assemble_report(
        self,
        sections: List[str],
        original_signals: List[Dict[str, Any]],
        use_llm: bool = True,
        user_query: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        組裝完整報告

        Args:
            sections: 各章節 Markdown 內容列表
            original_signals: 原始訊號列表
            use_llm: 是否使用 LLM 驅動邏輯
            user_query: 使用者查詢（可選）

        Returns:
            包含完整報告各部分的字典
        """
        if not sections:
            logger.warning("⚠️ 空章節列表 - 返回空報告")
            return {
                "markdown": "# 研究報告\n\n（無內容）",
                "summary": "空報告",
                "sources": "",
            }

        # 基本組裝
        full_report = "# 研究報告\n\n"

        # 添加使用者查詢上下文（如果有）
        if user_query:
            full_report += f"## 使用者意圖\n\n{user_query}\n\n---\n\n"

        # 添加各章節
        full_report += "\n\n".join(sections)

        # 添加摘要章節
        summary = self._generate_summary(sections, original_signals, user_query=user_query)
        full_report += f"\n\n---\n\n## 核心觀點摘要\n\n{summary}"

        # 添加參考文獻（從原始訊號提取）
        sources = self._extract_sources(original_signals)
        full_report += f"\n\n---\n\n{self._format_sources(sources)}"

        # 添加風險提示
        full_report += "\n\n---\n\n" + self._generate_disclaimer()

        if use_llm and self.llm_client:
            # 使用 LLM 進行最終編輯和優化
            logger.info("🤖 使用 LLM 進行最終報告組裝")

            try:
                prompt = get_final_assembly_instructions(
                    sources_list="\n".join([f"- {source}" for source in sources]),
                    market=self.market,
                )

                final_response = await self.llm_client.generate(
                    prompt=prompt,
                    json_mode=False,
                    temperature=0.5,
                    max_tokens=3072,
                )

                # 替換報告內容
                full_report = final_response

            except Exception as e:
                logger.error(f"❌ LLM 組裝失敗: {e}")
                logger.warning("🔄 使用基本組裝格式")

        logger.success("📋 報告組裝完成")
        return {
            "markdown": full_report,
            "summary": summary,
            "sources": "\n".join(sources) if sources else "（無來源）",
        }

    def _generate_summary(
        self,
        sections: List[str],
        signals: List[Dict[str, Any]],
        user_query: Optional[str] = None,
    ) -> str:
        """
        生成報告摘要

        Args:
            sections: 各章節內容
            signals: 原始訊號
            user_query: 使用者查詢（可選）

        Returns:
            摘要文本
        """
        # 簡單摘要：提取各章節標題和第一句
        summary_lines = []

        for section in sections:
            lines = section.split("\n")
            for line in lines:
                if line.startswith("## "):
                    summary_lines.append(f"- **{line.replace('## ', '')}**")
                    break
                elif line.startswith("### "):
                    summary_lines.append(f"  - {line.replace('### ', '')}")
                    break

        if not summary_lines:
            return "基於分析數據生成的研究報告"

        return "\n".join(summary_lines)

    def _extract_sources(self, signals: List[Dict[str, Any]]) -> List[str]:
        """
        從訊號中提取來源資訊

        Args:
            signals: 原始訊號列表

        Returns:
            來源列表
        """
        sources = set()

        for signal in signals:
            if isinstance(signal.get("sources"), list):
                for source in signal["sources"]:
                    if isinstance(source, dict) and source.get("url"):
                        sources.add(f"[{source.get('title', '無標題')}]({source.get('url')})")
                    elif isinstance(source, str):
                        sources.add(source)

        return sorted(list(sources))

    def _format_sources(self, sources: List[str]) -> str:
        """
        格式化來源為參考文獻格式

        Args:
            sources: 來源列表

        Returns:
            Markdown 參考文獻
        """
        if not sources:
            return "## 參考文獻\n\n（無來源資訊）"

        ref_lines = ["## 參考文獻"]
        for idx, source in enumerate(sources, 1):
            ref_lines.append(f"{idx}. {source}")

        return "\n".join(ref_lines)

    def _generate_disclaimer(self) -> str:
        """
        生成免責聲明（風險提示）

        Returns:
            風險提示文本
        """
        return """## 風險提示

本報告僅供參考，不構成投資建議。金融市場存在風險，投資需謹慎。
過去績效不保證未來表現。請根據自身風險承受能力做出投資決策。

---

*本報告由 AlphaEar 研究團隊生成 - 使用 AI 驅動的金融分析*
"""

    def _parse_to_json(self, markdown_report: str) -> Dict[str, Any]:
        """
        將 Markdown 報告解析為結構化 JSON

        Args:
            markdown_report: Markdown 格式報告

        Returns:
            結構化 JSON 報告
        """
        if not markdown_report or not markdown_report.strip():
            return {"error": "空報告"}

        lines = markdown_report.split("\n")

        # 提取標題
        title = "研究報告"
        for line in lines:
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                break

        # 提取章節
        sections = []
        current_section = None

        for line in lines:
            heading_match = re.match(r"^(#{2,4})\s+(.*)$", line.strip())
            if heading_match:
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "level": len(heading_match.group(1)),
                    "title": heading_match.group(2).strip(),
                    "content": "",
                }
                continue

            if current_section:
                if current_section["content"]:
                    current_section["content"] += "\n"
                current_section["content"] += line

        if current_section:
            sections.append(current_section)

        # 提取摘要
        summary = ""
        for section in sections:
            if "摘要" in section["title"]:
                summary = section["content"]
                break

        # 提取參考文獻
        references = []
        for section in sections:
            if "參考文獻" in section["title"]:
                references = [
                    {"index": idx + 1, "source": line.strip()}
                    for idx, line in enumerate(section["content"].split("\n"))
                    if line.strip()
                ]
                break

        return {
            "title": title,
            "sections": sections,
            "summary": summary,
            "references": references,
            "word_count": len(markdown_report.split()),
            "char_count": len(markdown_report),
        }

    def _simplify_for_line(self, markdown_report: str) -> str:
        """
        將報告簡化為 LINE 官方帳號友好格式

        Args:
            markdown_report: 原始 Markdown 報告

        Returns:
            LINE 友好格式的簡短文本
        """
        if not markdown_report:
            return ""

        # 移除 Markdown 格式
        clean_text = re.sub(r"[#*]", "", markdown_report)  # 移除標題和粗體
        clean_text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", clean_text)  # 移除連結但保留文字
        clean_text = re.sub(r"`.*?`", "", clean_text)  # 移除程式碼
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)  # 壓縮空行

        # 提取前 5 行或 500 字元
        lines = clean_text.split("\n")
        summary_lines = []
        char_count = 0

        for line in lines:
            if char_count < 500:
                summary_lines.append(line.strip())
                char_count += len(line) + 1  # +1 for newline
            else:
                break

        result = "\n".join(summary_lines).strip()

        # 添加來源資訊
        sources = re.findall(r"\[(.*?)\]\((.*?)\)", markdown_report)
        if sources:
            result += "\n\n📚 來源: " + ", ".join([f"{title}" for title, _ in sources[:3]])

        return result


__all__ = ["ReportGenerator"]