"""
API 速率限制器 - ZhipuAI API 并发控制和重试机制

功能:
- 使用 asyncio.Semaphore 控制最大并发数
- 自动检测 429 错误并重试
- 指数退避重试策略
- 统计和监控功能
- 线程局部存储，避免跨事件循环的 Semaphore 共享问题
"""

import asyncio
import os
import logging
import threading
import inspect
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

# 全局单例模式（所有线程共享同一个限流器实例）
_global_rate_limiter = None
_limiter_lock = threading.Lock()
_global_adaptive_rate_limiter = None
_adaptive_limiter_lock = threading.Lock()


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

        # 延迟初始化信号量（不在 __init__ 中创建，避免绑定到错误的事件循环）
        self._semaphore = None
        self._semaphore_loop = None

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

    async def _get_or_create_semaphore(self):
        """
        在当前事件循环中创建或获取 Semaphore

        这是解决跨事件循环问题的关键：Semaphore 在实际使用时创建，
        而不是在 __init__ 中创建，因此会绑定到当前的事件循环。
        同时检查当前 loop 是否与创建 semaphore 的 loop 一致，如果不一致则重建。
        """
        current_loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop != current_loop:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
            self._semaphore_loop = current_loop
            logger.debug(f"Created new Semaphore in current event loop (id: {id(current_loop)})")
        return self._semaphore

    async def __aenter__(self):
        """进入上下文管理器，获取信号量"""
        logger.info(f"🔒 Rate limiter: Attempting to acquire semaphore...")
        sem = await self._get_or_create_semaphore()
        logger.info(f"🔑 Rate limiter: Semaphore created/retrieved, waiting to acquire...")
        await sem.acquire()
        self._stats["total_calls"] += 1
        active = self.max_concurrent - sem._value
        logger.info(f"✅ Rate limiter: Semaphore acquired (active: {active}/{self.max_concurrent})")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器，释放信号量"""
        sem = await self._get_or_create_semaphore()
        sem.release()
        logger.debug(f"Released semaphore (active: {self.max_concurrent - sem._value}/{self.max_concurrent})")
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
            api_func: API 调用函数（可以是同步或异步函数）
            *args, **kwargs: 传递给 API 函数的参数

        Returns:
            API 响应结果
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # 执行 API 调用
                if inspect.iscoroutinefunction(api_func):
                    result = await api_func(*args, **kwargs)
                else:
                    result = api_func(*args, **kwargs)
                    if inspect.isawaitable(result):
                        result = await result

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


def get_api_rate_limiter() -> APIRateLimiter:
    """
    获取全局唯一的速率限制器实例（线程安全）

    所有线程共享同一个限流器实例，确保全局并发限制真正生效。
    使用双重检查锁定模式保证线程安全的初始化。

    Returns:
        APIRateLimiter 实例
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        with _limiter_lock:
            if _global_rate_limiter is None:
                _global_rate_limiter = APIRateLimiter()
                logger.info("Created global APIRateLimiter instance (shared across all threads)")
    return _global_rate_limiter


class AdaptiveAPIRateLimiter(APIRateLimiter):
    """
    自适应 API 速率限制器

    在基础速率限制器之上添加自适应并发控制：
    - 检测频繁的 429 错误并自动降低并发数
    - 支持手动启用监控模式（降低并发以避免与其他应用冲突）
    - 动态调整并发限制以优化性能
    """

    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None
    ):
        """
        初始化自适应速率限制器

        Args:
            max_concurrent: 最大并发数（默认从环境变量读取，或使用 3）
            max_retries: 最大重试次数（默认从环境变量读取，或使用 3）
            initial_backoff: 初始退避时间（秒，默认从环境变量读取，或使用 1.0）
        """
        super().__init__(max_concurrent, max_retries, initial_backoff)

        # 自适应控制参数
        self._current_concurrent_limit = self.max_concurrent  # 当前有效的并发限制
        self._recent_429_count = 0  # 最近的 429 错误计数
        self._429_threshold = 3  # 触发降级的 429 错误阈值
        self._last_429_time = None  # 上次 429 错误的时间

        logger.info(
            f"Adaptive API Rate Limiter initialized: max_concurrent={self.max_concurrent}, "
            f"adaptive_control enabled (429_threshold={self._429_threshold})"
        )

    def enable_monitoring_mode(self):
        """
        启用监控模式（降低并发数）

        当检测到与其他应用（如监控应用）的并发冲突时，
        可以手动调用此方法降低并发限制。
        """
        old_limit = self._current_concurrent_limit
        self._current_concurrent_limit = max(1, self.max_concurrent // 2)
        self._semaphore = None  # 重新创建信号量以应用新限制

        logger.warning(
            f"⚠️ Monitoring mode enabled. Concurrent limit reduced: "
            f"{old_limit} → {self._current_concurrent_limit}"
        )

    async def _get_or_create_semaphore(self):
        """
        在当前事件循环中创建或获取 Semaphore（使用自适应并发限制）
        """
        current_loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop != current_loop:
            self._semaphore = asyncio.Semaphore(self._current_concurrent_limit)
            self._semaphore_loop = current_loop
            logger.debug(
                f"Created new Semaphore with adaptive limit: {self._current_concurrent_limit} "
                f"(base: {self.max_concurrent}) in loop {id(current_loop)}"
            )
        return self._semaphore

    async def call_with_retry(
        self,
        api_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        执行 API 调用并自动重试（带自适应并发控制）

        当检测到频繁的 429 错误时，自动降低并发限制。

        Args:
            api_func: API 调用函数
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

                # 如果之前有 429 错误，逐步恢复并发限制
                if self._recent_429_count > 0 and attempt == 0:
                    self._gradually_restore_concurrent_limit()

                return result

            except Exception as e:
                last_exception = e
                error_str = str(e)

                # 检查是否为速率限制错误
                if is_rate_limit_error(e):
                    # 记录 429 错误
                    self._on_rate_limit_error()

                    if attempt < self.max_retries:
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
                        # 重试次数用尽
                        logger.error(
                            f"Max retries ({self.max_retries}) exceeded: {error_str[:200]}"
                        )
                        self._stats["failed_calls"] += 1
                        raise
                else:
                    # 非 429 错误
                    if attempt < self.max_retries:
                        logger.error(f"API call failed (non-rate-limit error): {error_str[:200]}")
                    else:
                        logger.error(f"Max retries ({self.max_retries}) exceeded: {error_str[:200]}")

                    self._stats["failed_calls"] += 1
                    raise

        # 理论上不会到达这里，但为了类型安全
        if last_exception:
            raise last_exception

    def _on_rate_limit_error(self):
        """
        处理速率限制错误

        当检测到 429 错误时，增加计数并检查是否需要降低并发限制。
        """
        import time

        self._recent_429_count += 1
        current_time = time.time()

        # 检查是否在短时间内频繁遇到 429
        if self._last_429_time and (current_time - self._last_429_time) < 30:
            # 30 秒内多次遇到 429，需要降低并发
            if self._recent_429_count >= self._429_threshold:
                old_limit = self._current_concurrent_limit
                self._current_concurrent_limit = max(1, self._current_concurrent_limit - 1)
                self._semaphore = None  # 重新创建信号量以应用新限制

                logger.warning(
                    f"⚠️ Frequent 429 errors detected. Reducing concurrent limit: "
                    f"{old_limit} → {self._current_concurrent_limit} "
                    f"(429 count: {self._recent_429_count})"
                )

                # 重置计数器以避免过度降级
                self._recent_429_count = 0
        else:
            # 距离上次 429 较久，重置计数
            self._recent_429_count = 1

        self._last_429_time = current_time

    def _gradually_restore_concurrent_limit(self):
        """
        逐步恢复并发限制

        当 API 调用成功时，逐步恢复并发限制到原始值。
        """
        if self._current_concurrent_limit < self.max_concurrent:
            self._current_concurrent_limit = min(
                self.max_concurrent,
                self._current_concurrent_limit + 1
            )
            self._semaphore = None  # 重新创建信号量以应用新限制

            logger.info(
                f"✅ Restoring concurrent limit: {self._current_concurrent_limit} "
                f"(target: {self.max_concurrent})"
            )

    def get_adaptive_stats(self) -> dict:
        """
        获取自适应统计信息

        Returns:
            包含基础统计和自适应控制数据的字典
        """
        stats = self.get_stats()
        stats.update({
            "current_concurrent_limit": self._current_concurrent_limit,
            "base_concurrent_limit": self.max_concurrent,
            "recent_429_count": self._recent_429_count,
            "adaptation_active": self._current_concurrent_limit < self.max_concurrent
        })
        return stats


def get_adaptive_api_rate_limiter() -> AdaptiveAPIRateLimiter:
    """
    获取全局唯一的自适应速率限制器实例（线程安全）

    所有线程共享同一个限流器实例，确保全局并发限制真正生效。
    使用双重检查锁定模式保证线程安全的初始化。

    Returns:
        AdaptiveAPIRateLimiter 实例
    """
    global _global_adaptive_rate_limiter
    if _global_adaptive_rate_limiter is None:
        with _adaptive_limiter_lock:
            if _global_adaptive_rate_limiter is None:
                _global_adaptive_rate_limiter = AdaptiveAPIRateLimiter()
                logger.info("Created global AdaptiveAPIRateLimiter instance (shared across all threads)")
    return _global_adaptive_rate_limiter
