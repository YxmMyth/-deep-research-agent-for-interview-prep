"""
Node 1: Planner

生成搜索计划，决定如何搜索 JD 和面经
"""

import json
import logging
from src.state import AgentState
from src.prompts.templates import PLANNER_PROMPT
from src.llm import call_llm_json

logger = logging.getLogger(__name__)


async def planner_node(state: AgentState) -> AgentState:
    """
    生成研究计划：为 JD 搜索和面经搜索分别生成关键词列表

    输入:
        - resume_content: 用户简历
        - target_position: 目标岗位

    输出:
        - jd_search_queries: JD 搜索关键词列表
        - interview_search_queries: 面经搜索关键词列表
    """
    logger.info("Running planner_node...")

    # 清理文本，确保有效的 UTF-8
    target_position = state["target_position"]
    resume_content = state["resume_content"]

    if isinstance(target_position, str):
        target_position = target_position.encode('utf-8', errors='ignore').decode('utf-8')
    if isinstance(resume_content, str):
        resume_content = resume_content.encode('utf-8', errors='ignore').decode('utf-8')

    # 构建 prompt
    prompt = PLANNER_PROMPT.format(
        target_position=target_position,
        resume_content=resume_content,
    )

    try:
        # 使用智谱 AI GLM-4 API
        result = await call_llm_json(prompt, model="glm-4.7", temperature=0.0)

        jd_queries = result.get("jd_search_queries", [])
        interview_queries = result.get("interview_search_queries", [])

        logger.info(f"Generated {len(jd_queries)} JD queries and {len(interview_queries)} interview queries")

        return {
            "jd_search_queries": jd_queries,
            "interview_search_queries": interview_queries,
        }

    except Exception as e:
        logger.error(f"Failed to parse planner response: {e}")
        # 回退到默认查询
        default_jd_queries = [
            f"{target_position} 招聘",
            f"{target_position} job description",
        ]
        default_interview_queries = [
            f"{target_position} 面经",
            f"{target_position} interview experience",
        ]

        return {
            "jd_search_queries": default_jd_queries,
            "interview_search_queries": default_interview_queries,
        }
