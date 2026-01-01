"""
Agent State 定义
使用 TypedDict 定义 LangGraph 工作流中的状态结构
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import Required
import operator


class CompanyInfo(TypedDict):
    """公司基础信息"""
    name: Required[str]
    description: Optional[str]
    industry: Optional[str]
    website: Optional[str]


class TechStack(TypedDict):
    """技术栈信息"""
    language: str
    percentage: float
    repository_count: int


class GitHubStats(TypedDict):
    """GitHub 统计数据"""
    organization: str
    total_repositories: int
    top_repos: List[Dict[str, Any]]
    language_distribution: List[TechStack]
    echarts_config: Optional[str]  # ECharts JSON 配置


class NewsArticle(TypedDict):
    """新闻文章"""
    title: str
    url: str
    summary: str
    published_date: Optional[str]
    source: Optional[str]


class InterviewExperience(TypedDict):
    """面试经验"""
    title: str
    content: str
    source: str
    url: Optional[str]


class AgentState(TypedDict):
    """
    Agent 主状态类
    包含工作流中所有节点需要共享的数据
    """
    # 用户输入
    company_name: Required[str]
    user_query: Optional[str]

    # 工具调用状态
    need_news_search: bool
    need_github_stats: bool
    need_interview_exp: bool

    # 收集的数据
    company_info: Optional[CompanyInfo]
    github_stats: Optional[GitHubStats]
    news_articles: List[NewsArticle]
    interview_experiences: List[InterviewExperience]

    # 分析结果
    analysis_summary: Optional[str]
    key_insights: List[str]

    # 最终输出
    final_report: Optional[str]

    # 错误处理
    errors: Annotated[List[str], operator.add]

    # 元数据
    current_step: str
    iteration_count: int


def create_initial_state(company_name: str, user_query: str = "") -> AgentState:
    """
    创建初始状态

    Args:
        company_name: 目标公司名称
        user_query: 用户的额外查询需求

    Returns:
        初始化的 AgentState
    """
    return {
        "company_name": company_name,
        "user_query": user_query,
        "need_news_search": True,
        "need_github_stats": True,
        "need_interview_exp": True,
        "company_info": None,
        "github_stats": None,
        "news_articles": [],
        "interview_experiences": [],
        "analysis_summary": None,
        "key_insights": [],
        "final_report": None,
        "errors": [],
        "current_step": "init",
        "iteration_count": 0,
    }
