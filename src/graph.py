"""
LangGraph 工作流定义

定义整个 Agent 的执行流程：
1. Planner -> 2. Researchers (并行) -> 3. Analyst -> 4. Writer -> 5. Critic (Reflexion循环)
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.state import AgentState
from src.nodes import (
    planner_node,
    jd_researcher_node,
    interview_researcher_node,
    gap_analyst_node,
    report_writer_node,
    critic_node,
)


def should_revise(state: AgentState) -> str:
    """
    判断是否需要修改报告

    Args:
        state: 当前 Agent 状态

    Returns:
        "revise" 或 "approve"
    """
    critique = state.get("critique", "")
    revision_count = state.get("revision_count", 0)

    # 如果 Critic 批准，结束循环
    if "APPROVED" in critique:
        return "approve"

    # 最多修改 3 次
    if revision_count >= 3:
        return "approve"

    # 否则继续修改
    return "revise"


def build_graph() -> CompiledStateGraph:
    """
    构建完整的 LangGraph 工作流

    工作流结构:
                    ┌──────────────────────────────────┐
                    │           Planner                 │
                    └──────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌──────────────────┐          ┌──────────────────────┐
    │ JD Researcher    │          │ Interview Researcher │
    └──────────────────┘          └──────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
                    ┌──────────────────────────────────┐
                    │          Gap Analyst             │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │         Report Writer            │◄────┐
                    └──────────────────────────────────┘     │
                              │                             │
                              ▼                             │
                    ┌──────────────────────────────────┐     │
                    │            Critic                │────┘
                    └──────────────────────────────────┘
    """
    builder = StateGraph(AgentState)

    # 添加节点
    builder.add_node("planner", planner_node)
    builder.add_node("jd_researcher", jd_researcher_node)  # Worker A
    builder.add_node("interview_researcher", interview_researcher_node)  # Worker B
    builder.add_node("gap_analyst", gap_analyst_node)
    builder.add_node("report_writer", report_writer_node)
    builder.add_node("critic", critic_node)

    # 定义边

    # 1. 开始 -> Planner
    builder.add_edge(START, "planner")

    # 2. Sequential: Planner 之后串行执行两个 Researcher（避免429错误）
    builder.add_edge("planner", "jd_researcher")
    builder.add_edge("jd_researcher", "interview_researcher")

    # 3. Fan-in: 两个 Researcher 都完成后进入 Analyst
    builder.add_edge("interview_researcher", "gap_analyst")

    # 4. Analyst -> Writer
    builder.add_edge("gap_analyst", "report_writer")

    # 5. Writer -> Critic
    builder.add_edge("report_writer", "critic")

    # 6. Reflexion Loop: Critic 决定下一步
    builder.add_conditional_edges(
        "critic",
        should_revise,
        {
            "revise": "report_writer",  # 回到 Writer 重写
            "approve": END,  # 结束流程
        },
    )

    # 编译 Graph
    return builder.compile()
