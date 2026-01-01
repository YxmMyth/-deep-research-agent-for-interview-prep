"""
GitHub Stats Tool - 自定义工具
通过 GitHub API 获取公司的开源仓库技术栈分布
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

import requests
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubStatsInput(BaseModel):
    """GitHub Stats Tool 输入参数"""
    company_name: str = Field(
        description="公司名称，用于搜索 GitHub 组织",
        example="DeepSeek"
    )
    top_n: int = Field(
        default=5,
        description="分析的仓库数量",
        ge=1,
        le=20
    )


class GitHubStatsTool:
    """
    GitHub 统计工具

    功能：
    1. 根据公司名搜索 GitHub 组织
    2. 获取该组织的 Top N 仓库
    3. 统计主要编程语言的分布
    4. 生成 ECharts 配置 JSON

    错误处理：
    - 组织不存在 → 返回默认空值
    - API 限流 → 记录日志并返回默认值
    - 网络错误 → 重试 3 次
    """

    def __init__(self, github_token: Optional[str] = None):
        """
        初始化 GitHub API 客户端

        Args:
            github_token: GitHub Personal Access Token（可选，但推荐使用以提高速率限制）
        """
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DeepResearchAgent/1.0"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 默认返回值（当搜索失败时）
        self.default_response = {
            "organization": "Unknown",
            "total_repositories": 0,
            "top_repos": [],
            "language_distribution": [
                {"language": "Unknown", "percentage": 100.0, "repository_count": 0}
            ],
            "echarts_config": None,
            "error": "No data available"
        }

    def _search_organization(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        搜索 GitHub 组织

        Args:
            company_name: 公司名称

        Returns:
            组织信息字典，如果未找到则返回 None
        """
        search_url = f"{self.base_url}/search/users"
        params = {
            "q": f"{company_name} in:login type:org",
            "per_page": 5
        }

        try:
            response = self._make_request(search_url, params=params)
            if response and response.get("items"):
                # 返回第一个匹配的组织
                return response["items"][0]
            return None
        except Exception as e:
            logger.error(f"搜索组织失败: {e}")
            return None

    def _get_organization_repos(
        self,
        org_login: str,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取组织的仓库列表（按 stars 排序）

        Args:
            org_login: 组织登录名
            top_n: 返回的仓库数量

        Returns:
            仓库列表
        """
        repos_url = f"{self.base_url}/orgs/{org_login}/repos"
        params = {
            "sort": "stars",
            "direction": "desc",
            "per_page": top_n
        }

        try:
            repos = self._make_request(repos_url, params=params)
            return repos if repos else []
        except Exception as e:
            logger.error(f"获取仓库列表失败: {e}")
            return []

    def _calculate_language_distribution(
        self,
        repos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        计算语言分布

        Args:
            repos: 仓库列表

        Returns:
            语言分布列表，格式：[{"language": str, "percentage": float, "repository_count": int}]
        """
        language_stats: Dict[str, int] = {}

        for repo in repos:
            language = repo.get("language", "Unknown")
            if language:
                language_stats[language] = language_stats.get(language, 0) + 1

        total_repos = len(repos)
        if total_repos == 0:
            return [
                {
                    "language": "Unknown",
                    "percentage": 100.0,
                    "repository_count": 0
                }
            ]

        distribution = []
        for lang, count in sorted(
            language_stats.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            distribution.append({
                "language": lang,
                "percentage": round((count / total_repos) * 100, 2),
                "repository_count": count
            })

        return distribution

    def _generate_echarts_config(
        self,
        org_name: str,
        distribution: List[Dict[str, Any]]
    ) -> str:
        """
        生成 ECharts 饼图配置 JSON

        Args:
            org_name: 组织名称
            distribution: 语言分布数据

        Returns:
            ECharts 配置 JSON 字符串
        """
        # 准备数据
        data = [
            {"value": item["percentage"], "name": item["language"]}
            for item in distribution
        ]

        # ECharts 配置
        config = {
            "title": {
                "text": f"{org_name} - 技术栈分布",
                "left": "center",
                "textStyle": {
                    "fontSize": 18,
                    "fontWeight": "bold"
                }
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}: {c}% ({d}%)"
            },
            "legend": {
                "orient": "vertical",
                "left": "left",
                "top": "middle"
            },
            "series": [
                {
                    "name": "编程语言",
                    "type": "pie",
                    "radius": "50%",
                    "data": data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    },
                    "label": {
                        "formatter": "{b}\n{c}%"
                    }
                }
            ]
        }

        return json.dumps(config, ensure_ascii=False, indent=2)

    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Optional[Any]:
        """
        发起 HTTP 请求（带重试机制）

        Args:
            url: 请求 URL
            params: 查询参数
            max_retries: 最大重试次数

        Returns:
            响应 JSON 数据，失败返回 None
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)

                # 检查速率限制
                if response.status_code == 403:
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    logger.warning(f"GitHub API 速率限制触发，剩余请求: {remaining}")
                    return None

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"请求超时，重试 {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error("请求超时，已达最大重试次数")
                    return None

            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败: {e}，重试 {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error("请求失败，已达最大重试次数")
                    return None

        return None

    def run(self, company_name: str, top_n: int = 5) -> Dict[str, Any]:
        """
        执行 GitHub 统计分析（主入口）

        Args:
            company_name: 公司名称
            top_n: 分析的仓库数量

        Returns:
            包含统计数据的字典
        """
        logger.info(f"开始分析公司: {company_name}")

        # 1. 搜索组织
        org_info = self._search_organization(company_name)
        if not org_info:
            logger.warning(f"未找到组织: {company_name}")
            return self.default_response

        org_login = org_info["login"]
        logger.info(f"找到组织: {org_login}")

        # 2. 获取仓库
        repos = self._get_organization_repos(org_login, top_n)
        if not repos:
            logger.warning(f"组织 {org_login} 没有仓库")
            return {
                **self.default_response,
                "organization": org_login
            }

        logger.info(f"获取到 {len(repos)} 个仓库")

        # 3. 计算语言分布
        distribution = self._calculate_language_distribution(repos)
        logger.info(f"语言分布: {distribution}")

        # 4. 生成 ECharts 配置
        echarts_config = self._generate_echarts_config(org_login, distribution)

        # 5. 组装结果
        result = {
            "organization": org_login,
            "total_repositories": org_info.get("public_repos", 0),
            "top_repos": [
                {
                    "name": repo["name"],
                    "stars": repo["stargazers_count"],
                    "language": repo.get("language", "Unknown"),
                    "description": repo.get("description", ""),
                    "url": repo["html_url"]
                }
                for repo in repos
            ],
            "language_distribution": distribution,
            "echarts_config": echarts_config
        }

        logger.info(f"分析完成: {org_login}")
        return result

    @staticmethod
    def get_langchain_tool() -> StructuredTool:
        """
        返回 LangChain 兼容的 Tool 对象

        Returns:
            StructuredTool 实例
        """
        tool_instance = GitHubStatsTool()

        def _run(company_name: str, top_n: int = 5) -> str:
            """LangChain 调用入口"""
            result = tool_instance.run(company_name, top_n)
            return json.dumps(result, ensure_ascii=False, indent=2)

        return StructuredTool.from_function(
            func=_run,
            name="github_stats",
            description="""
            获取公司的 GitHub 开源技术栈分布。

            输入：公司名称（如 "DeepSeek", "ByteDance"）
            输出：
            - 组织基本信息
            - Top 5 热门仓库
            - 编程语言分布（百分比）
            - ECharts 饼图配置 JSON

            适用场景：分析目标公司的技术栈和工程能力
            """,
            args_schema=GitHubStatsInput
        )


# 便捷函数
def get_github_stats(company_name: str, top_n: int = 5) -> Dict[str, Any]:
    """
    便捷函数：直接获取 GitHub 统计

    Args:
        company_name: 公司名称
        top_n: 分析的仓库数量

    Returns:
        统计结果字典
    """
    tool = GitHubStatsTool()
    return tool.run(company_name, top_n)


if __name__ == "__main__":
    # 测试代码
    result = get_github_stats("DeepSeek", top_n=5)
    print(json.dumps(result, ensure_ascii=False, indent=2))
