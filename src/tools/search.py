"""
Tavily Search 封装

用于搜索 JD 和面经的统一接口
"""

import os
from typing import List
from tavily import TavilyClient
import logging

logger = logging.getLogger(__name__)


def tavily_search(
    query: str, max_results: int = 10, search_depth: str = "advanced"
) -> List[str]:
    """
    使用 Tavily API 进行搜索，返回 URL 列表

    Args:
        query: 搜索关键词
        max_results: 最多返回结果数 (默认 10)
        search_depth: 搜索深度 ("basic" 或 "advanced")

    Returns:
        URL 列表

    Raises:
        ValueError: API Key 未设置或搜索失败时抛出异常

    Example:
        >>> urls = tavily_search("字节跳动 后端开发 JD 2026校招")
        >>> print(urls)
        ['https://jobs.bytedance.com/...', 'https://www.nowcoder.com/...']
    """
    # 获取 API Key
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is not set")

    try:
        # 初始化 Tavily Client
        client = TavilyClient(api_key=api_key)

        logger.info(f"Searching with query: {query}")

        # 执行搜索
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_domains=[],  # 不限制域名
            exclude_domains=[],  # 不排除域名
        )

        # 提取 URL 列表
        urls = [result["url"] for result in response.get("results", [])]

        logger.info(f"Found {len(urls)} URLs for query: {query}")
        return urls

    except Exception as e:
        error_msg = f"Tavily search failed: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def tavily_search_with_content(
    query: str, max_results: int = 10, search_depth: str = "advanced"
) -> List[dict]:
    """
    使用 Tavily API 进行搜索，返回包含内容和摘要的结果

    Args:
        query: 搜索关键词
        max_results: 最多返回结果数
        search_depth: 搜索深度

    Returns:
        包含 url, title, content, score 的字典列表

    Example:
        >>> results = tavily_search_with_content("字节跳动 面经")
        >>> print(results[0]["title"])
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is not set")

    try:
        client = TavilyClient(api_key=api_key)

        logger.info(f"Searching with content for query: {query}")

        response = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_domains=[],
            exclude_domains=[],
        )

        # 返回完整结果
        results = response.get("results", [])
        logger.info(f"Found {len(results)} results with content")
        return results

    except Exception as e:
        error_msg = f"Tavily search with content failed: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
