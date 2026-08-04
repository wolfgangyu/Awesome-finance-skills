"""
預設 LLM 客戶端實作

使用現有的 ModelRouter 來提供標準的 LLMClient 介面實作
"""

from typing import Optional
from loguru import logger
from .base_client import LLMClient


class DefaultLLMClient(LLMClient):
    """
    預設 LLM 客戶端實作

    使用現有的 ModelRouter 來生成文本，並實作標準的 LLMClient 介面。
    這是 alphaear-reporter 的主要 LLM 後端實作。

    Attributes:
        router: ModelRouter 實例，用於實際的模型路由和生成
        market: 當前設定的市場類型
    """

    def __init__(self, router: Optional["ModelRouter"] = None):
        """
        初始化 DefaultLLMClient

        Args:
            router: ModelRouter 實例。如果未提供，將使用全局單例 router
        """
        self.router = router if router is not None else ModelRouter()
        self.market: str = "tw"  # 預設市場為台灣
        logger.info(f"🤖 DefaultLLMClient initialized with market: {self.market}")

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        使用 ModelRouter 生成文本內容

        Args:
            prompt: 輸入的提示文本
            json_mode: 是否啟用 JSON 模式
            temperature: 控制生成隨機性的參數
            max_tokens: 生成的最大 token 數

        Returns:
            生成的文本內容
        """
        logger.debug(f"📝 Generating text for market: {self.market}")
        logger.debug(f"📝 Prompt length: {len(prompt)} characters")

        # 根據市場設定調整提示
        market_prompt = self._apply_market_context(prompt)

        try:
            result = await self.router.get_reasoning_model().generate(
                messages=[
                    {
                        "role": "user",
                        "content": market_prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )

            logger.debug(f"✅ Text generated successfully (chars: {len(result)})")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to generate text: {e}")
            raise LLMGenerationError(f"LLM generation failed: {e}") from e

    def set_market(self, market: str) -> None:
        """
        設定市場類型

        影響後續生成的 prompt 內容，讓模型能根據特定市場生成更準確的報告

        Args:
            market: 市場類型代碼，例如 "tw" (台灣)、"us" (美國)、"cn" (中國)
        """
        if not isinstance(market, str):
            raise TypeError(f"market must be a string, got {type(market)}")

        if not market:
            raise ValueError("market cannot be empty")

        self.market = market.lower()
        logger.info(f"🏢 Market set to: {self.market}")

    def _apply_market_context(self, prompt: str) -> str:
        """
        根據市場設定調整提示內容

        為提示添加市場相關的上下文資訊，幫助模型生成更準確的報告

        Args:
            prompt: 原始提示

        Returns:
            添加市場上下文後的提示
        """
        market_context = {
            "tw": "台灣市場",
            "us": "美國市場",
            "both": "台美市場",
        }

        context = market_context.get(self.market, "全球市場")

        # 添加市場上下文到提示
        enhanced_prompt = f"""
# 市場上下文: {context}

{prompt}
        """.strip()

        return enhanced_prompt

    def __repr__(self) -> str:
        """提供可讀的字串表示"""
        return f"DefaultLLMClient(market='{self.market}')"


class LLMGenerationError(Exception):
    """LLM 文本生成失敗時拋出的異常"""
    pass


__all__ = ["DefaultLLMClient", "LLMGenerationError"]