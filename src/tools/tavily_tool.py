"""
Tavily Search Tool - 封装
用于搜索公司新闻、文化、面试经验等
"""

import os
from typing import List, Dict, Any, Optional
from langchain_community.tools.tavily_search import TavilySearchResults


class TavilySearchTool:
    """
    Tavily 搜索工具的封装

    功能：
    - 搜索公司新闻
    - 搜索企业文化
    - 搜索面试经验
    """

    def __init__(self, api_key: Optional[str] = None, max_results: int = 10):
        """
        初始化 Tavily 搜索工具

        Args:
            api_key: Tavily API Key
            max_results: 最大返回结果数
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY 环境变量未设置")

        self.max_results = max_results
        self.tool = TavilySearchResults(
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
        )

    def search_company_news(
        self,
        company_name: str
    ) -> List[Dict[str, Any]]:
        """
        搜索公司相关新闻

        Args:
            company_name: 公司名称

        Returns:
            新闻列表
        """
        query = f"{company_name} company news latest updates"
        results = self.tool._run(query)

        # Tavily 返回的可能是 tuple 或 list
        if isinstance(results, tuple):
            results = list(results)
        if not isinstance(results, list):
            print(f"  Warning: Tavily returned unexpected type: {type(results)}")
            return []

        articles = []
        for result in results:
            # 确保每个 result 是字典
            if not isinstance(result, dict):
                continue

            articles.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "summary": result.get("content", ""),
                "published_date": None,  # Tavily 可能不提供
                "source": "Tavily"
            })

        return articles

    def search_interview_experiences(
        self,
        company_name: str
    ) -> List[Dict[str, Any]]:
        """
        搜索面试经验

        Args:
            company_name: 公司名称

        Returns:
            面试经验列表
        """
        query = f"{company_name} interview experience questions 面经"
        results = self.tool._run(query)

        # Tavily 返回的可能是 tuple 或 list
        if isinstance(results, tuple):
            results = list(results)
        if not isinstance(results, list):
            print(f"  Warning: Tavily returned unexpected type: {type(results)}")
            return []

        experiences = []
        for result in results:
            # 确保每个 result 是字典
            if not isinstance(result, dict):
                continue

            experiences.append({
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "source": "Tavily",
                "url": result.get("url", "")
            })

        return experiences

    def search_company_culture(
        self,
        company_name: str
    ) -> str:
        """
        搜索企业文化

        Args:
            company_name: 公司名称

        Returns:
            企业文化摘要
        """
        query = f"{company_name} company culture work environment values"
        results = self.tool._run(query)

        if results:
            # 汇总所有结果
            summaries = [r.get("content", "") for r in results]
            return "\n\n".join(summaries[:3])  # 取前 3 条

        return ""


def get_tavily_tool() -> TavilySearchTool:
    """
    便捷函数：获取 Tavily 工具实例

    Returns:
        TavilySearchTool 实例
    """
    return TavilySearchTool()
