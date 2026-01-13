"""
API 速率限制器 - ZhipuAI API 并发控制和重试机制

功能:
- 使用 asyncio.Semaphore 控制最大并发数
- 自动检测 429 错误并重试
- 指数退避重试策略
- 统计和监控功能
"""

import asyncio
import os
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """
    ZhipuAI API 速率限制器

    使用信号量控制并发 API 调用数量，防止触发 429 错误。
    遇到速率限制时自动使用指数退避策略重试。
    """

    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None
    ):
        """
        初始化速率限制器

        Args:
            max_concurrent: 最大并发数（默认从环境变量读取，或使用 3）
            max_retries: 最大重试次数（默认从环境变量读取，或使用 3）
            initial_backoff: 初始退避时间（秒，默认从环境变量读取，或使用 1.0）
        """
        # 从环境变量读取配置
        self.max_concurrent = max_concurrent or int(os.getenv("ZHIPUAI_MAX_CONCURRENT", "3"))
        self.max_retries = max_retries or int(os.getenv("ZHIPUAI_MAX_RETRIES", "3"))
        self.initial_backoff = initial_backoff or float(os.getenv("ZHIPUAI_INITIAL_BACKOFF", "1.0"))

        # 创建信号量
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        # 统计信息
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "rate_limited_calls": 0,
            "retries": 0,
            "failed_calls": 0
        }

        logger.info(
            f"API Rate Limiter initialized: max_concurrent={self.max_concurrent}, "
            f"max_retries={self.max_retries}, initial_backoff={self.initial_backoff}s"
        )

    async def __aenter__(self):
        """进入上下文管理器，获取信号量"""
        await self._semaphore.acquire()
        self._stats["total_calls"] += 1
        logger.debug(f"Acquired semaphore (active: {self._semaphore._value}/{self.max_concurrent})")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器，释放信号量"""
        self._semaphore.release()
        logger.debug(f"Released semaphore (active: {self._semaphore._value}/{self.max_concurrent})")
        return False

    async def call_with_retry(
        self,
        api_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        执行 API 调用并自动重试

        Args:
            api_func: API 调用函数（必须是同步函数，因为 ZhipuAI SDK 是同步的）
            *args, **kwargs: 传递给 API 函数的参数

        Returns:
            API 响应结果

        Raises:
            Exception: 重试次数用尽后仍失败时抛出原始异常
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # 执行 API 调用
                result = api_func(*args, **kwargs)

                # 记录成功
                if attempt == 0:
                    self._stats["successful_calls"] += 1

                return result

            except Exception as e:
                last_exception = e
                error_str = str(e)

                # 检查是否为速率限制错误
                if is_rate_limit_error(e) and attempt < self.max_retries:
                    # 计算退避时间（指数退避）
                    backoff_time = self.initial_backoff * (2 ** attempt)
                    self._stats["rate_limited_calls"] += 1
                    self._stats["retries"] += 1

                    logger.warning(
                        f"Rate limited (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"waiting {backoff_time:.1f}s before retry... "
                        f"Error: {error_str[:200]}"
                    )

                    # 等待后重试
                    await asyncio.sleep(backoff_time)
                    continue
                else:
                    # 非 429 错误或重试次数用尽
                    if attempt < self.max_retries:
                        logger.error(f"API call failed (non-rate-limit error): {error_str[:200]}")
                    else:
                        logger.error(f"Max retries ({self.max_retries}) exceeded: {error_str[:200]}")

                    self._stats["failed_calls"] += 1
                    raise

        # 理论上不会到达这里，但为了类型安全
        if last_exception:
            raise last_exception

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            包含统计数据的字典
        """
        return self._stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "rate_limited_calls": 0,
            "retries": 0,
            "failed_calls": 0
        }


def is_rate_limit_error(error: Exception) -> bool:
    """
    检查是否为速率限制错误（429 或相关错误码）

    Args:
        error: 异常对象

    Returns:
        如果是速率限制错误返回 True，否则返回 False
    """
    error_str = str(error).lower()

    # 检查多种速率限制相关的标识
    rate_limit_indicators = [
        "429",  # HTTP 429 状态码
        "1302",  # ZhipuAI 并发限制错误码
        "rate limit",  # 通用速率限制
        "并发",  # 中文"并发"
        "concurrent",  # 英文"并发"
        "quota",  # 配额限制
        "too many requests",  # 请求过多
    ]

    return any(indicator in error_str for indicator in rate_limit_indicators)


# 全局单例
_rate_limiter_instance: Optional[APIRateLimiter] = None


def get_api_rate_limiter() -> APIRateLimiter:
    """
    获取全局速率限制器实例（单例模式）

    Returns:
        APIRateLimiter 实例
    """
    global _rate_limiter_instance

    if _rate_limiter_instance is None:
        _rate_limiter_instance = APIRateLimiter()

    return _rate_limiter_instance


def reset_api_rate_limiter():
    """
    重置全局速率限制器（主要用于测试）
    """
    global _rate_limiter_instance
    _rate_limiter_instance = None
