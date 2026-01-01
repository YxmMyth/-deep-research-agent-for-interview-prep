"""
LangGraph 工作流定义
构建深度调研 Agent 的状态图
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

from .state import AgentState, create_initial_state
from .nodes import (
    router_node,
    tool_node,
    analyst_node,
    reporter_node,
)
from .nodes.router import intent_router


def create_research_graph():
    """
    创建深度调研工作流图

    图结构：
    ┌──────────────────────────────────────────────────────────────┐
    │                                                              │
    │  START → Router → Tools → Router → Tools → ... → Analyst   │
    │                      ↓                                       │
    │                   Reporter → END                             │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘

    节点说明：
    - Router: 决定需要调用哪些工具
    - Tools: 执行工具调用（GitHub、Tavily）
    - Analyst: 汇总分析数据
    - Reporter: 生成最终报告

    Returns:
        编译后的 LangGraph StateGraph
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("router", router_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("reporter", reporter_node)

    # 设置入口点
    workflow.set_entry_point("router")

    # 添加边（连接节点）

    # 1. Router → Tools 或 Analyst（条件边）
    workflow.add_conditional_edges(
        "router",
        intent_router,
        {
            "tools": "tools",
            "analyst": "analyst"
        }
    )

    # 2. Tools → Router（循环回路由判断）
    workflow.add_edge("tools", "router")

    # 3. Analyst → Reporter
    workflow.add_edge("analyst", "reporter")

    # 4. Reporter → END
    workflow.add_edge("reporter", END)

    # 编译图，设置递归限制
    app = workflow.compile()

    return app


def run_research_agent(
    company_name: str,
    user_query: str = "",
    verbose: bool = True
) -> dict:
    """
    运行深度调研 Agent

    Args:
        company_name: 目标公司名称
        user_query: 用户额外查询需求
        verbose: 是否打印详细信息

    Returns:
        最终状态字典（包含报告）
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"Starting Deep Research Agent")
        print(f"{'='*60}")
        print(f"Target Company: {company_name}")
        if user_query:
            print(f"Additional Query: {user_query}")
        print(f"{'='*60}\n")

    # 创建图
    graph = create_research_graph()

    # 初始化状态
    initial_state = create_initial_state(company_name, user_query)

    # 执行工作流
    try:
        final_state = graph.invoke(initial_state)

        if verbose:
            print(f"\n{'='*60}")
            print(f"Research Completed")
            print(f"{'='*60}")
            print(f"Collected Data:")
            print(f"  - News: {len(final_state.get('news_articles', []))} articles")
            print(f"  - Interview Experiences: {len(final_state.get('interview_experiences', []))} articles")
            print(f"  - GitHub: {'OK' if final_state.get('github_stats') else 'Failed'}")
            print(f"{'='*60}\n")

        return final_state

    except Exception as e:
        if verbose:
            print(f"\nExecution Failed: {str(e)}")
        raise


def get_markdown_report(company_name: str, user_query: str = "") -> str:
    """
    便捷函数：直接获取 Markdown 报告

    Args:
        company_name: 目标公司名称
        user_query: 用户额外查询需求

    Returns:
        Markdown 报告文本
    """
    final_state = run_research_agent(company_name, user_query, verbose=False)
    return final_state.get("final_report", "报告生成失败")


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        company = sys.argv[1]
    else:
        company = "DeepSeek"

    result = run_research_agent(company)

    # 保存报告
    report = result.get("final_report", "")
    if report:
        filename = f"{company}_report.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 报告已保存到: {filename}")
