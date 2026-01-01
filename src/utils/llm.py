"""
LLM 初始化工具
根据配置创建 LLM 实例
"""

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..config import config


def get_llm(temperature: float = None, model: str = None):
    """
    根据配置获取 LLM 实例

    Args:
        temperature: 温度参数（可选，覆盖配置）
        model: 模型名称（可选，覆盖配置）

    Returns:
        ChatOpenAI 或 ChatAnthropic 实例
    """
    provider = config.llm.provider
    model_name = model or config.llm.model
    temp = temperature if temperature is not None else config.llm.temperature

    if provider == "openai":
        return ChatOpenAI(
            model=model_name,
            temperature=temp,
            max_tokens=config.llm.max_tokens,
            api_key=config.api.openai_api_key
        )
    elif provider == "anthropic":
        return ChatAnthropic(
            model=model_name,
            temperature=temp,
            max_tokens=config.llm.max_tokens,
            api_key=config.api.anthropic_api_key
        )
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
