# Task 1: LLM 抽象介面

**專案脈絡**：
本任務是 alphaear-reporter 統一設計的第一步，目標是建立 LLM 抽象介面，讓後續的 ReportGenerator 可以相容不同的 LLM 後端（Claude Code、Hermes Agent、Polaris 後端）。

**檔案**：
- Create: `skills/alphaear-reporter/scripts/utils/llm/base_client.py`
- Create: `skills/alphaear-reporter/scripts/utils/llm/default_client.py`
- Modify: `skills/alphaear-reporter/scripts/utils/llm/router.py:1-50`
- Test: `tests/test_llm_client.py`

**介面定義**：
```python
from abc import ABC, abstractmethod
from typing import Optional

class LLMClient(ABC):
    """抽象 LLM Client 介面"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """生成文本"""
        pass

    @abstractmethod
    def set_market(self, market: str):
        """設定市場類型（影響 prompt 生成）"""
        pass
```

**預設實作**：
```python
from .base_client import LLMClient
from .router import LLMRouter  # 現有實作

class DefaultLLMClient(LLMClient):
    def __init__(self, router: LLMRouter):
        self.router = router

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """使用現有的 LLMRouter 生成文本"""
        return await self.router.generate(
            prompt=prompt,
            json_mode=json_mode,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def set_market(self, market: str):
        """設定市場類型"""
        self.router.set_market(market)
```

**相容性修改**：
確保 `LLMRouter` 有以下方法（現有實作可能已有）：
```python
async def generate(
    self,
    prompt: str,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """現有實作"""
    # ... 保持現有邏輯不變
```

**測試**：
```python
import pytest
from skills.alphaear-reporter.scripts.utils.llm.default_client import DefaultLLMClient
from skills.alphaear-reporter.scripts.utils.llm.router import LLMRouter

@pytest.mark.asyncio
async def test_default_llm_client():
    router = LLMRouter()  # 假設 LLMRouter 有 mock 實作
    client = DefaultLLMClient(router)

    # 測試 generate 方法
    result = await client.generate("Hello", json_mode=False)
    assert isinstance(result, str)

    # 測試 set_market 方法
    client.set_market("tw")
    assert router.market == "tw"  # 假設 LLMRouter 有 market 屬性
```

**報告契約**：
實作完成後，請在報告中提供以下資訊：
1. 完成的 commit hash（多個 commit 請提供範圍）
2. 測試結果摘要（通過/失敗數量）
3. 任何疑慮或問題
4. 是否需要額外上下文