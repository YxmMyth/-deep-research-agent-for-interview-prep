"""
LLM 调用封装 - 使用智谱 AI GLM-4 API

统一封装 LLM 调用接口，便于切换不同的 LLM 提供商
"""

import os
import json
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from typing import Optional
import logging
import asyncio

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 从环境变量获取 API Key
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")
if not ZHIPUAI_API_KEY:
    raise ValueError("ZHIPUAI_API_KEY environment variable is not set")

# 初始化智谱 AI 客户端
client = ZhipuAI(api_key=ZHIPUAI_API_KEY)

# 导入速率限制器获取函数（不在这里初始化，避免模块级别绑定）
from src.api_rate_limiter import get_api_rate_limiter


async def call_llm(
    prompt: str,
    model: str = "glm-4.7",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    result_format: str = "message",
    timeout: int = 120,
) -> str:
    """
    调用智谱 AI GLM-4 API

    Args:
        prompt: 用户提示词
        model: 模型名称，默认 glm-4.7
               可选: glm-4, glm-4-plus, glm-4-air, glm-4-flash 等
        temperature: 温度参数，控制随机性
        max_tokens: 最大生成 token 数
        result_format: 返回格式（保留参数兼容性）

    Returns:
        模型生成的文本内容

    Raises:
        Exception: API 调用失败时抛出异常
    """
    # 定义 API 调用函数（异步封装）
    async def _api_call():
        logger.info(f"Calling ZhipuAI API with model: {model}")

        def _sync_call():
            return client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return await asyncio.to_thread(_sync_call)

    try:
        # 在函数内部获取当前线程的速率限制器（避免模块级别绑定）
        rate_limiter = get_api_rate_limiter()
        logger.info(f"Acquiring rate limiter (max_concurrent=3)...")

        # 使用速率限制器包装 API 调用
        async with rate_limiter:
            logger.info(f"Semaphore acquired, calling API...")
            response = await asyncio.wait_for(
                rate_limiter.call_with_retry(_api_call),
                timeout=timeout,
            )

            # 提取生成的内容
            content = response.choices[0].message.content
            logger.info(f"Successfully generated {len(content)} characters")
            return content

    except Exception as e:
        error_msg = f"Failed to call ZhipuAI API: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e


async def call_llm_with_system_message(
    system_message: str,
    user_message: str,
    model: str = "glm-4.7",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout: int = 120,
) -> str:
    """
    调用智谱 AI GLM-4 API（支持系统消息）

    Args:
        system_message: 系统消息（设置角色和行为）
        user_message: 用户消息
        model: 模型名称，默认 glm-4
        temperature: 温度参数
        max_tokens: 最大生成 token 数
        timeout: 超时时间（秒），默认120秒

    Returns:
        模型生成的文本内容
    """
    # 定义 API 调用函数（异步封装）
    async def _api_call():
        logger.info(f"Calling ZhipuAI API with system message, model: {model}")

        def _sync_call():
            return client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

        return await asyncio.to_thread(_sync_call)

    try:
        # 在函数内部获取当前线程的速率限制器（避免模块级别绑定）
        rate_limiter = get_api_rate_limiter()
        logger.info(f"Acquiring rate limiter (max_concurrent=3)...")

        # 使用速率限制器包装 API 调用
        async with rate_limiter:
            logger.info(f"Semaphore acquired, calling API with system message...")
            # 添加超时保护
            response = await asyncio.wait_for(
                rate_limiter.call_with_retry(_api_call),
                timeout=timeout
            )

            # 提取生成的内容
            content = response.choices[0].message.content
            logger.info(f"Successfully generated {len(content)} characters")
            return content

    except asyncio.TimeoutError:
        error_msg = f"API call timed out after {timeout} seconds"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Failed to call ZhipuAI API: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e


async def call_llm_json(
    prompt: str,
    model: str = "glm-4.7",
    temperature: float = 0.0,
    timeout: int = 120,
) -> dict:
    """
    调用智谱 AI GLM-4 API（返回 JSON 格式）

    Args:
        prompt: 用户提示词（应包含要求返回 JSON 的指令）
        model: 模型名称，默认 glm-4
        temperature: 温度参数，默认 0.0 以确保确定性输出

    Returns:
        解析后的 JSON 字典

    Raises:
        Exception: API 调用失败或 JSON 解析失败时抛出异常
    """
    try:
        # 调用 LLM
        content = await call_llm(
            prompt=prompt,
            model=model,
            temperature=temperature,
            result_format="message",
            timeout=timeout,
        )

        # 提取 JSON 部分
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.rfind("```")
            content = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.rfind("```")
            content = content[json_start:json_end].strip()

        # 解析 JSON
        result = json.loads(content)
        logger.info("Successfully parsed JSON response")
        return result

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse JSON response: {str(e)}"
        logger.error(f"{error_msg}\nResponse content: {content[:500]}")
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to call LLM for JSON output: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
