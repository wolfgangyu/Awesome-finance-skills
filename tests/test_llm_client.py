import pytest
from skills.alphaear-reporter.scripts.utils.llm.default_client import DefaultLLMClient
from skills.alphaear-reporter.scripts.utils.llm.router import ModelRouter


class MockModelRouter:
    """Mock ModelRouter for testing"""

    def __init__(self):
        self.market = "tw"
        self.model = MockReasoningModel()

    def get_reasoning_model(self):
        return self.model


class MockReasoningModel:
    """Mock ReasoningModel for testing"""

    async def generate(self, messages, temperature, max_tokens, json_mode=False):
        prompt = messages[0]["content"]
        return f"Mock response for: {prompt[:50]}..."


@pytest.fixture
def mock_router():
    return MockModelRouter()


@pytest.mark.asyncio
async def test_default_llm_client_generate(mock_router):
    """Test DefaultLLMClient.generate method"""
    client = DefaultLLMClient(mock_router)

    # Test basic generation
    result = await client.generate("Test prompt")
    assert isinstance(result, str)
    assert "Mock response" in result

    # Test with parameters
    result = await client.generate(
        "Test prompt",
        json_mode=True,
        temperature=0.5,
        max_tokens=1000
    )
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_default_llm_client_json_mode(mock_router):
    """Test DefaultLLMClient.generate with json_mode=True"""
    client = DefaultLLMClient(mock_router)
    result = await client.generate("Test prompt", json_mode=True)
    assert isinstance(result, str)
    assert "Mock response" in result


@pytest.mark.asyncio
async def test_default_llm_client_set_market(mock_router):
    """Test DefaultLLMClient.set_market method"""
    client = DefaultLLMClient(mock_router)

    # Test setting market
    client.set_market("us")
    assert client.market == "us"

    # Test market context in prompt
    result = await client.generate("Test prompt")
    assert "美國市場" in result


@pytest.mark.asyncio
async def test_default_llm_client_market_context(mock_router):
    """Test DefaultLLMClient market context application"""
    client = DefaultLLMClient(mock_router)

    # Test Taiwan market context
    client.set_market("tw")
    result = await client.generate("Test prompt")
    assert "台灣市場" in result

    # Test US market context
    client.set_market("us")
    result = await client.generate("Test prompt")
    assert "美國市場" in result

    # Test both market context
    client.set_market("both")
    result = await client.generate("Test prompt")
    assert "台美市場" in result


@pytest.mark.asyncio
async def test_default_llm_client_error_handling(mock_router):
    """Test DefaultLLMClient error handling"""
    client = DefaultLLMClient(mock_router)

    # Test invalid market type
    with pytest.raises(TypeError):
        client.set_market(123)

    # Test empty market
    with pytest.raises(ValueError):
        client.set_market("")

    # Test LLM generation error (mock router raises exception)
    class FailingMockRouter:
        def get_reasoning_model(self):
            class FailingModel:
                async def generate(self, messages, temperature, max_tokens, json_mode=False):
                    raise RuntimeError("Mock LLM failure")
            return FailingModel()

    failing_client = DefaultLLMClient(FailingMockRouter())
    with pytest.raises(LLMGenerationError):
        await failing_client.generate("Test prompt")