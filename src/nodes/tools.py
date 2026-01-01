"""
Tool Node - 工具执行节点
执行具体的搜索和 API 调用
"""

from typing import Dict, Any, List
import json

from ..state import AgentState, NewsArticle, InterviewExperience, GitHubStats, CompanyInfo
from ..tools.github_tool import GitHubStatsTool
from ..tools.tavily_tool import TavilySearchTool


def tool_node(state: AgentState) -> Dict[str, Any]:
    """
    工具节点：根据需求执行相应的工具调用

    逻辑：
    1. 检查 need_* 标志位
    2. 调用相应的工具
    3. 更新状态

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    print("\n[Tool Node] Executing tool calls...")

    company_name = state["company_name"]
    updates = {}
    errors = []

    # 1. GitHub 技术栈分析
    if state["need_github_stats"]:
        print(f"  -> Calling GitHub Stats Tool: {company_name}")
        try:
            github_tool = GitHubStatsTool()
            stats = github_tool.run(company_name, top_n=5)
            updates["github_stats"] = stats
            print(f"    [OK] Got {stats['total_repositories']} repositories")
        except Exception as e:
            error_msg = f"GitHub Stats call failed: {str(e)}"
            errors.append(error_msg)
            print(f"    [FAILED] {error_msg}")

    # 2. 公司新闻搜索
    if state["need_news_search"]:
        print(f"  -> Calling Tavily to search news: {company_name}")
        try:
            tavily_tool = TavilySearchTool()
            news = tavily_tool.search_company_news(company_name)
            updates["news_articles"] = [
                NewsArticle(
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    summary=article.get("summary", ""),
                    published_date=article.get("published_date"),
                    source=article.get("source", "Tavily")
                )
                for article in news
            ]
            print(f"    [OK] Got {len(news)} news articles")
        except Exception as e:
            error_msg = f"News search failed: {str(e)}"
            errors.append(error_msg)
            print(f"    [FAILED] {error_msg}")

    # 3. 面试经验搜索
    if state["need_interview_exp"]:
        print(f"  -> Calling Tavily to search interview experiences: {company_name}")
        try:
            tavily_tool = TavilySearchTool()
            experiences = tavily_tool.search_interview_experiences(company_name)
            updates["interview_experiences"] = [
                InterviewExperience(
                    title=exp.get("title", ""),
                    content=exp.get("content", ""),
                    source=exp.get("source", "Tavily"),
                    url=exp.get("url")
                )
                for exp in experiences
            ]
            print(f"    [OK] Got {len(experiences)} interview experiences")
        except Exception as e:
            error_msg = f"Interview experience search failed: {str(e)}"
            errors.append(error_msg)
            print(f"    [FAILED] {error_msg}")

    # 4. 补充公司基础信息（如果有新闻数据）
    if state["need_news_search"] and not state.get("company_info"):
        try:
            tavily_tool = TavilySearchTool()
            culture = tavily_tool.search_company_culture(company_name)
            updates["company_info"] = CompanyInfo(
                name=company_name,
                description=culture[:500] if culture else "",
                industry="Technology",  # 默认值
                website=""
            )
        except Exception as e:
            errors.append(f"Company info retrieval failed: {str(e)}")

    # 更新步数
    updates["current_step"] = "tools_executed"
    updates["iteration_count"] = state["iteration_count"] + 1

    # 添加错误
    if errors:
        updates["errors"] = errors

    return updates
