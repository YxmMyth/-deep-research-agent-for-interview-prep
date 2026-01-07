"""
简单的限流机制，用于防止API滥用

使用场景：
- Hugging Face Spaces在线服务
- 防止单个IP过度使用
- 控制总体使用量

策略：
- 每个IP每天最多5次请求
- 全局每天最多100次请求
- 使用Hugging Face Datasets持久化存储（可选）
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import json


class RateLimiter:
    """基于内存的简单限流器"""

    def __init__(
        self,
        max_requests_per_ip: int = 5,
        max_total_requests: int = 100
    ):
        """
        初始化限流器

        Args:
            max_requests_per_ip: 每个IP每天的最大请求数
            max_total_requests: 全局每天的最大请求数
        """
        self.max_requests_per_ip = max_requests_per_ip
        self.max_total_requests = max_total_requests

        # 使用内存存储（Hugging Face Spaces重启后会重置）
        # 格式: {date: "2025-01-07", ip_counts: {"1.2.3.4": 3, ...}, total_count: 50}
        self._storage: Dict = {
            "date": self._get_today(),
            "ip_counts": {},
            "total_count": 0
        }

    def _get_today(self) -> str:
        """获取今天的日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")

    def _reset_if_new_day(self):
        """如果是新的一天，重置计数器"""
        today = self._get_today()
        if self._storage["date"] != today:
            self._storage = {
                "date": today,
                "ip_counts": {},
                "total_count": 0
            }

    def check_rate_limit(self, ip_address: str) -> tuple[bool, str]:
        """
        检查是否超过限流

        Args:
            ip_address: 客户端IP地址

        Returns:
            (是否允许, 错误消息)
        """
        self._reset_if_new_day()

        # 检查全局限流
        if self._storage["total_count"] >= self.max_total_requests:
            return False, f"🚫 **今日配额已用完**\n\n全局每日限额：{self.max_total_requests}次\n今日已使用：{self._storage['total_count']}次\n\n💡 **建议**：明天再试，或[本地部署](https://github.com/你的用户名/DeepResearchAgentV2)使用自己的API Key"

        # 检查IP限流
        ip_count = self._storage["ip_counts"].get(ip_address, 0)
        if ip_count >= self.max_requests_per_ip:
            return False, f"🚫 **你的今日配额已用完**\n\n每个IP每日限额：{self.max_requests_per_ip}次\n你今日已使用：{ip_count}次\n\n💡 **建议**：明天再试，或[本地部署](https://github.com/你的用户名/DeepResearchAgentV2)使用自己的API Key"

        return True, ""

    def record_request(self, ip_address: str):
        """
        记录一次请求

        Args:
            ip_address: 客户端IP地址
        """
        self._reset_if_new_day()

        # 更新IP计数
        self._storage["ip_counts"][ip_address] = self._storage["ip_counts"].get(ip_address, 0) + 1

        # 更新全局计数
        self._storage["total_count"] += 1

    def get_stats(self) -> Dict:
        """获取当前统计信息"""
        self._reset_if_new_day()
        return {
            "date": self._storage["date"],
            "total_requests": self._storage["total_count"],
            "unique_ips": len(self._storage["ip_counts"]),
            "max_requests_per_ip": self.max_requests_per_ip,
            "max_total_requests": self.max_total_requests
        }


# 全局限流器实例（单例）
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            max_requests_per_ip=5,
            max_total_requests=100
        )
    return _rate_limiter


def check_rate_limit(ip_address: str = "unknown") -> tuple[bool, str]:
    """
    检查是否允许请求

    Args:
        ip_address: 客户端IP地址（如果无法获取，使用"unknown"）

    Returns:
        (是否允许, 错误消息)
    """
    limiter = get_rate_limiter()
    allowed, error_msg = limiter.check_rate_limit(ip_address)

    if allowed:
        limiter.record_request(ip_address)

    return allowed, error_msg


def get_usage_stats() -> Dict:
    """获取使用统计（用于监控）"""
    limiter = get_rate_limiter()
    return limiter.get_stats()
