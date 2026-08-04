"""
LLM 抽象客戶端介面

定義標準的 LLM 客戶端介面，讓 ReportGenerator 可以相容不同的 LLM 後端
（Claude Code、Hermes Agent、Polaris 後端等）
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMClient(ABC):
    """
    抽象 LLM Client 介面

    定義所有 LLM 客戶端必須實作的標準方法，確保不同後端的相容性。
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        生成文本內容

        Args:
            prompt: 輸入的提示文本
            json_mode: 是否啟用 JSON 模式（確保輸出為有效 JSON）
            temperature: 控制生成隨機性的參數 (0.0 完全確定性, 1.0 完全隨機)
            max_tokens: 生成的最大 token 數

        Returns:
            生成的文本內容
        """
        pass

    @abstractmethod
    def set_market(self, market: str) -> None:
        """
        設定市場類型

        影響後續生成的 prompt 內容，讓模型能根據特定市場生成更準確的報告

        Args:
            market: 市場類型代碼，例如 "tw" (台灣)、"us" (美國)、"cn" (中國)
        """
        pass

    def __repr__(self) -> str:
        """提供可讀的字串表示"""
        return f"{self.__class__.__name__}()"


__all__ = ["LLMClient"]