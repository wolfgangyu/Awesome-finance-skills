import os

from typing import Optional, List, Dict, Any

from agno.agent import Agent

from agno.models.base import Model

from loguru import logger

from .factory import get_model



def test_tool_call_support(model: Model) -> bool:

    """

    測試模型是否支援原生的 Tool Call (Function Calling)。

    透過嘗試執行一個簡單的加法工具來驗證。

    """

    def get_current_weather(location: str):

        """取得指定地點的天氣"""

        return f"{location} 的天氣是晴天，25度。"



    test_agent = Agent(

        model=model,

        tools=[get_current_weather],

        instructions="請呼叫工具查詢北京的天氣，並直接回傳工具的輸出結果。"

    )



    try:

        # 執行一個簡單的任務，觀察是否觸發了 tool_call

        response = test_agent.run("北京天氣怎麼樣？")

        

        # 檢查 response 中是否套件含 tool_calls

        # Agno 的 RunResponse 物件通常套件含 messages，我們可以檢查最後幾條訊息

        has_tool_call = False

        for msg in response.messages:

            if hasattr(msg, 'tool_calls') and msg.tool_calls:

                has_tool_call = True

                break

        

        if has_tool_call:

            logger.info(f"✅ Model {model.id} supports native tool calling.")

            return True

        else:

            # 如果沒有 tool_calls 但回傳了正確答案，可能是模型透過純文字模擬了工具呼叫（ReAct）

            # 或者根本沒用工具。對於原生支援的判斷，我們堅持要求有 tool_calls 結構。

            logger.warning(f"⚠️ Model {model.id} did NOT use native tool calling structure.")

            return False

            

    except Exception as e:

        logger.error(f"❌ Error testing tool call for {model.id}: {e}")

        return False



class ModelCapabilityRegistry:

    """

    模型能力登錄檔，用於快取和管理不同模型的能力測試結果。

    """

    _cache = {}



    @classmethod

    def get_capabilities(cls, provider: str, model_id: str, **kwargs) -> Dict[str, bool]:

        key = f"{provider}:{model_id}"

        if key not in cls._cache:

            logger.info(f"🔍 Testing capabilities for {key}...")

            model = get_model(provider, model_id, **kwargs)

            supports_tool_call = test_tool_call_support(model)

            cls._cache[key] = {

                "supports_tool_call": supports_tool_call

            }

        return cls._cache[key]



if __name__ == "__main__":

    # 簡單測試指令碼

    from dotenv import load_dotenv

    load_dotenv()

    

    # 測試當前配置的模型

    p = os.getenv("LLM_PROVIDER", "ust")

    m = os.getenv("LLM_MODEL", "Qwen")

    

    print(f"Testing {p}/{m}...")

    res = ModelCapabilityRegistry.get_capabilities(p, m)

    print(f"Result: {res}")

