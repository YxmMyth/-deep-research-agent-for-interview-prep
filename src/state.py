"""
LangGraph AgentState definition

定义整个工作流的全局状态结构
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict
from operator import add

from src.schemas import JobDescriptionSchema, InterviewLogSchema, GapAnalysisResult


class AgentState(TypedDict):
    """Graph 的全局状态"""

    # ===== 输入 =====
    resume_content: str  # 用户简历内容
    target_position: str  # 目标岗位
    analysis_mode: str  # 分析模式: "quick" 或 "standard"
    quick_mode_config: dict  # 快速模式配置（可选）

    # ===== Node 1 (Planner) 输出 =====
    jd_search_queries: list[str]  # JD 搜索关键词列表
    interview_search_queries: list[str]  # 面经搜索关键词列表

    # ===== Node 2 (Researchers) 输出 =====
    # 使用 Annotated + add 实现列表累加（并行写入）
    job_descriptions: Annotated[list[JobDescriptionSchema], add]
    interview_logs: Annotated[list[InterviewLogSchema], add]

    # ===== Node 3 (Analyst) 输出 =====
    gap_analysis: Optional[GapAnalysisResult]

    # ===== Node 4 (Writer + Critic) 输出 =====
    draft_report: str  # 初稿报告
    critique: str  # Critic 评审意见
    final_report: str  # 最终报告
    revision_count: int  # 修订次数
