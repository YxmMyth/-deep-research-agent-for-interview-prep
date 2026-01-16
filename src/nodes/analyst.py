"""
Node 3: Gap Analyst

进行三重对比分析：
1. 简历 vs JD
2. JD vs 面经
3. 简历 vs 面经
"""

import json
import logging
from src.state import AgentState
from src.schemas import GapAnalysisResult, UserProfile
from src.prompts.templates import GAP_ANALYSIS_PROMPT
from src.prompts.personalization import get_personalized_prompts
from src.llm import call_llm

logger = logging.getLogger(__name__)


async def gap_analyst_node(state: AgentState) -> AgentState:
    """
    对比分析简历、JD 和面经，找出技能差距

    输入:
        - resume_content: 用户简历
        - target_position: 目标岗位
        - user_profile: 用户画像（用于个性化）
        - job_descriptions: JD 列表
        - interview_logs: 面经列表

    输出:
        - gap_analysis: GapAnalysisResult 对象
    """
    logger.info("Running gap_analyst_node...")

    # 获取用户画像（用于个性化）
    user_profile = state.get("user_profile", UserProfile())

    # 准备数据摘要
    jd_count = len(state.get("job_descriptions", []))
    interview_count = len(state.get("interview_logs", []))

    # JD 摘要
    jd_summary = ""
    for i, jd in enumerate(state.get("job_descriptions", []), 1):
        jd_summary += f"""
JD #{i} - {jd.company_name} - {jd.position_title}
必需技能: {", ".join(jd.required_skills[:10])}
加分技能: {", ".join(jd.preferred_skills[:5])}
来源: {jd.source_url}
---
"""

    # 面经摘要
    interview_summary = ""
    for i, log in enumerate(state.get("interview_logs", []), 1):
        questions_summary = []
        for round_info in log.rounds[:3]:  # 只展示前3轮
            questions_summary.append(
                f"{round_info.round_name}: {len(round_info.questions)}个问题"
            )

        interview_summary += f"""
面经 #{i} - {log.company_name} - {log.position_title}
结果: {log.overall_result or '未知'}
考察技能: {", ".join(log.key_skills_tested[:10])}
面试轮次: {", ".join(questions_summary)}
来源: {log.source_url}
---
"""

    # 构建 prompt（先格式化基础模板）
    base_prompt = GAP_ANALYSIS_PROMPT.format(
        resume_content=state["resume_content"],
        target_position=state["target_position"],
        jd_count=jd_count,
        jd_summary=jd_summary.strip(),
        interview_count=interview_count,
        interview_summary=interview_summary.strip(),
    )

    # 应用个性化提示词（Gap 分析也需要个性化，不同经验水平关注点不同）
    prompt = get_personalized_prompts(user_profile, base_prompt)
    logger.info(f"Using personalized gap analysis prompt (experience: {user_profile.experience_level})")

    # 使用智谱 AI GLM-4 进行分析
    try:
        # 调用 LLM 并获取 JSON 响应
        response_content = await call_llm(prompt, model="glm-4.7", temperature=0.0)

        # 提取 JSON 部分
        content = response_content
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.rfind("```")
            content = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.rfind("```")
            content = content[json_start:json_end].strip()

        # 解析并验证
        result = json.loads(content)
        gap_analysis = GapAnalysisResult.model_validate(result)

        logger.info(
            f"Gap analysis completed. Found {len(gap_analysis.resume_vs_jd)} resume vs JD gaps, "
            f"{len(gap_analysis.jd_vs_interview)} JD vs interview gaps, "
            f"{len(gap_analysis.resume_vs_interview)} resume vs interview gaps"
        )

        return {"gap_analysis": gap_analysis}

    except Exception as e:
        logger.error(f"Failed to parse gap analysis response: {e}")

        # 返回空的 GapAnalysisResult
        empty_result = GapAnalysisResult()
        return {"gap_analysis": empty_result}
