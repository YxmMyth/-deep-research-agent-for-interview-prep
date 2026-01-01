"""
Router Node - 路由节点
分析用户意图，决定需要调用哪些工具
"""

from typing import Literal, Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState
from ..tools.github_tool import GitHubStatsTool
from ..tools.tavily_tool import TavilySearchTool


def router_node(state: AgentState) -> Dict[str, Any]:
    """
    路由节点：分析用户意图，决定数据收集策略

    逻辑：
    1. 检查已收集的数据
    2. 判断哪些数据仍需获取
    3. 如果超过最大迭代次数，强制进入分析
    4. 更新 need_* 标志位

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    print("\n[Router Node] Analyzing data collection needs...")

    company_name = state["company_name"]
    iteration = state["iteration_count"]

    # 防止无限循环：超过 3 次迭代后强制进入分析
    if iteration >= 3:
        print("  [Warning] Max iterations reached, forcing analysis phase")
        return {
            "need_news_search": False,
            "need_github_stats": False,
            "need_interview_exp": False,
            "current_step": "analysis"
        }

    # 初始化所有需求为 True
    updates = {
        "need_news_search": True,
        "need_github_stats": True,
        "need_interview_exp": True,
        "current_step": "routing"
    }

    # 检查已收集的数据
    if state.get("news_articles") and len(state["news_articles"]) > 0:
        updates["need_news_search"] = False
        print("  [OK] News data collected")

    if state.get("github_stats"):
        updates["need_github_stats"] = False
        print("  [OK] GitHub tech stack data collected")

    if state.get("interview_experiences") and len(state["interview_experiences"]) > 0:
        updates["need_interview_exp"] = False
        print("  [OK] Interview experiences collected")

    # 如果所有数据都已收集，跳转到分析阶段
    needs_collection = any([
        updates["need_news_search"],
        updates["need_github_stats"],
        updates["need_interview_exp"]
    ])

    if not needs_collection:
        print("  -> All data collected, entering analysis phase")
        updates["current_step"] = "analysis"
    else:
        print(f"  -> Need to continue collecting data (iteration {iteration + 1})")

    return updates


def intent_router(state: AgentState) -> Literal["tools", "analyst"]:
    """
    条件边函数：决定下一步是工具调用还是分析

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    # 如果还有数据需要收集，前往 tools 节点
    if any([
        state["need_news_search"],
        state["need_github_stats"],
        state["need_interview_exp"]
    ]):
        return "tools"

    # 否则进入分析阶段
    return "analyst"
