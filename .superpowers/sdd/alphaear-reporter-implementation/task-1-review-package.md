# Review Package — Task 1: LLM Abstract Interface

## Commits
```
7f605c6 feat(reporter): add LLMClient abstract interface and default implementation
```

## Diff Stat
```
skills/alphaear-reporter/scripts/utils/llm/base_client.py   | 58 +++++++
skills/alphaear-reporter/scripts/utils/llm/default_client.py | 136 ++++++++++++++++++++
tests/test_llm_client.py                                     | 75 +++++++++++
3 files changed, 269 insertions(+)
```

## Full Diff
```diff
diff --git a/skills/alphaear-reporter/scripts/utils/llm/base_client.py b/skills/alphaear-reporter/scripts/utils/llm/base_client.py
new file mode 100644
index 0000000..b54be1b
--- /dev/null
+++ b/skills/alphaear-reporter/scripts/utils/llm/base_client.py
@@ -0,0 +1,58 @@
+"""
+LLM 抽象客戶端介面
+
+定義標準的 LLM 客戶端介面，讓 ReportGenerator 可以相容不同的 LLM 後端
+（Claude Code、Hermes Agent、Polaris 後端等）
+"""
+
+from abc import ABC, abstractmethod
+from typing import Optional
+
+
+class LLMClient(ABC):
+    """
+    抽象 LLM Client 介面
+
+    定義所有 LLM 客戶端必須實作的標準方法，確保不同後端的相容性。
+    """
+
+    @abstractmethod
+    async def generate(
+        self,
+        prompt: str,
+        json_mode: bool = False,
+        temperature: float = 0.7,
+        max_tokens: int = 4096,
+    ) -> str:
+        """
+        生成文本內容
+
+        Args:
+            prompt: 輸入的提示文本
+            json_mode: 是否啟用 JSON 模式（確保輸出為有效 JSON）
+            temperature: 控制生成隨機性的參數 (0.0 完全確定性, 1.0 完全隨機)
+            max_tokens: 生成的最大 token 數
+
+        Returns:
+            生成的文本內容
+        """
+        pass
+
+    @abstractmethod
+    def set_market(self, market: str) -> None:
+        """
+        設定市場類型
+
+        影響後續生成的 prompt 內容，讓模型能根據特定市場生成更準確的報告
+
+        Args:
+            market: 市場類型代碼，例如 "tw" (台灣)、"us" (美國)、"cn" (中國)
+        """
+        pass
+
+    def __repr__(self) -> str:
+        """提供可讀的字串表示"""
+        return f"{self.__class__.__name__}()"
+
+
+__all__ = ["LLMClient"]
diff --git a/skills/alphaear-reporter/scripts/utils/llm/default_client.py b/skills/alphaear-reporter/scripts/utils/llm/default_client.py
new file mode 100644
index 0000000..cfb9437
--- /dev/null
+++ b/skills/alphaear-reporter/scripts/utils/llm/default_client.py
@@ -0,0 +1,136 @@
+"""
+預設 LLM 客戶端實作
+
+使用現有的 ModelRouter 來提供標準的 LLMClient 介面實作
+"""
+
+from typing import Optional
+from loguru import logger
+from .base_client import LLMClient
+from .router import ModelRouter
+
+
+class DefaultLLMClient(LLMClient):
+    """
+    預設 LLM 客戶端實作
+
+    使用現有的 ModelRouter 來生成文本，並實作標準的 LLMClient 介面。
+    這是 alphaear-reporter 的主要 LLM 後端實作。
+    """
+
+    def __init__(self, router: Optional[ModelRouter] = None):
+        self.router = router if router is not None else ModelRouter()
+        self.market: str = "tw"
+        logger.info(f"🤖 DefaultLLMClient initialized with market: {self.market}")
+
+    async def generate(
+        self,
+        prompt: str,
+        json_mode: bool = False,
+        temperature: float = 0.7,
+        max_tokens: int = 4096,
+    ) -> str:
+        logger.debug(f"📝 Generating text for market: {self.market}")
+        logger.debug(f"📝 Prompt length: {len(prompt)} characters")
+
+        market_prompt = self._apply_market_context(prompt)
+
+        try:
+            result = await self.router.get_reasoning_model().generate(
+                messages=[{"role": "user", "content": market_prompt}],
+                temperature=temperature,
+                max_tokens=max_tokens,
+                json_mode=json_mode,
+            )
+            logger.debug(f"✅ Text generated successfully (chars: {len(result)})")
+            return result
+        except Exception as e:
+            logger.error(f"❌ Failed to generate text: {e}")
+            raise
+
+    def set_market(self, market: str) -> None:
+        if not isinstance(market, str):
+            raise TypeError(f"market must be a string, got {type(market)}")
+        if not market:
+            raise ValueError("market cannot be empty")
+        self.market = market.lower()
+        logger.info(f"🏢 Market set to: {self.market}")
+
+    def _apply_market_context(self, prompt: str) -> str:
+        market_context = {
+            "tw": "台灣市場",
+            "us": "美國市場",
+            "cn": "中國市場",
+            "hk": "香港市場",
+            "jp": "日本市場",
+            "kr": "韓國市場"
+        }
+        context = market_context.get(self.market, "全球市場")
+        enhanced_prompt = f"""
+# 市場上下文: {context}
+
+{prompt}
+        """.strip()
+        return enhanced_prompt
+
+    def __repr__(self) -> str:
+        return f"DefaultLLMClient(market='{self.market}')"
+
+
+__all__ = ["DefaultLLMClient"]
diff --git a/tests/test_llm_client.py b/tests/test_llm_client.py
new file mode 100644
index 0000000..cb1e287
--- /dev/null
+++ b/tests/test_llm_client.py
@@ -0,0 +1,75 @@
+import pytest
+from skills.alphaear-reporter.scripts.utils.llm.default_client import DefaultLLMClient
+from skills.alphaear-reporter.scripts.utils.llm.router import ModelRouter
+
+
+class MockModelRouter:
+    def __init__(self):
+        self.market = "tw"
+        self.model = MockReasoningModel()
+
+    def get_reasoning_model(self):
+        return self.model
+
+
+class MockReasoningModel:
+    async def generate(self, messages, temperature, max_tokens, json_mode=False):
+        prompt = messages[0]["content"]
+        return f"Mock response for: {prompt[:50]}..."
+
+
+@pytest.fixture
+def mock_router():
+    return MockModelRouter()
+
+
+@pytest.mark.asyncio
+async def test_default_llm_client_generate(mock_router):
+    client = DefaultLLMClient(mock_router)
+    result = await client.generate("Test prompt")
+    assert isinstance(result, str)
+    assert "Mock response" in result
+
+    result = await client.generate(
+        "Test prompt", json_mode=True, temperature=0.5, max_tokens=1000
+    )
+    assert isinstance(result, str)
+
+
+@pytest.mark.asyncio
+async def test_default_llm_client_set_market(mock_router):
+    client = DefaultLLMClient(mock_router)
+    client.set_market("us")
+    assert client.market == "us"
+    result = await client.generate("Test prompt")
+    assert "美國市場" in result
+
+
+@pytest.mark.asyncio
+async def test_default_llm_client_error_handling(mock_router):
+    client = DefaultLLMClient(mock_router)
+    with pytest.raises(TypeError):
+        client.set_market(123)
+    with pytest.raises(ValueError):
+        client.set_market("")
+```