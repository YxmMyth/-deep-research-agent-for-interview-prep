"""
Node 4: Writer and Critic

- report_writer: 生成备战报告
- critic: 评审报告质量，决定是否需要重写（Reflexion循环）
"""

import logging
from src.state import AgentState
from src.prompts.templates import REPORT_WRITER_PROMPT, CRITIC_CHECKLIST
from src.prompts.personalization import get_personalized_prompts, get_urgent_mode_prompt
from src.schemas import UserProfile
from src.llm import call_llm

logger = logging.getLogger(__name__)


async def report_writer_node(state: AgentState) -> AgentState:
    """
    基于 Gap 分析结果生成备战报告

    输入:
        - resume_content: 用户简历
        - target_position: 目标岗位
        - gap_analysis: Gap 分析结果
        - user_profile: 用户画像（用于个性化）
        - revision_count: 当前修订次数
        - critique: 评审意见（如果有）

    输出:
        - draft_report: 生成的报告
        - final_report: 最终报告（如果是第一次生成）
        - revision_count: 更新的修订次数
    """
    revision_count = state.get("revision_count", 0)
    logger.info(f"Running report_writer_node (revision {revision_count})...")

    gap_analysis = state.get("gap_analysis")
    if not gap_analysis:
        logger.warning("No gap analysis available, generating generic report")
        gap_analysis = {"resume_vs_jd": [], "jd_vs_interview": [], "resume_vs_interview": []}

    # 获取用户画像（用于个性化）
    user_profile = state.get("user_profile", UserProfile())

    # 准备 Gap 分析的文本描述
    def format_gaps(gaps, title):
        if not gaps:
            return f"## {title}\n未发现明显差距\n"
        output = f"## {title}\n\n"
        for gap in gaps[:10]:  # 限制显示数量
            output += f"- **{gap.skill_name}** ({gap.priority}优先级)\n"
            output += f"  - 类型: {gap.gap_type}\n"
            output += f"  - 证据: {gap.evidence}\n\n"
        return output

    resume_vs_jd_analysis = format_gaps(gap_analysis.resume_vs_jd, "简历 vs JD")
    jd_vs_interview_analysis = format_gaps(gap_analysis.jd_vs_interview, "JD vs 面经")
    resume_vs_interview_analysis = format_gaps(
        gap_analysis.resume_vs_interview, "简历 vs 面经"
    )

    # 构建 prompt（先格式化基础模板）
    base_prompt = REPORT_WRITER_PROMPT.format(
        target_position=state["target_position"],
        resume_content=state["resume_content"],
        resume_vs_jd_analysis=resume_vs_jd_analysis,
        jd_vs_interview_analysis=jd_vs_interview_analysis,
        resume_vs_interview_analysis=resume_vs_interview_analysis,
    )

    # 应用个性化提示词
    # 如果准备时间≤2周，使用紧急模式；否则使用标准个性化
    if user_profile.preparation_time_weeks <= 2:
        prompt = get_urgent_mode_prompt(base_prompt)
        logger.info(f"Using urgent mode prompt (preparation_time: {user_profile.preparation_time_weeks} weeks)")
    else:
        prompt = get_personalized_prompts(user_profile, base_prompt)
        logger.info(f"Using personalized prompt (experience: {user_profile.experience_level}, style: {user_profile.learning_style})")

    # 如果有评审意见，将其加入 prompt
    if revision_count > 0 and state.get("critique"):
        prompt += f"""
## 之前的评审意见

{state['critique']}

请根据以上评审意见修改报告，解决所有指出的问题。
"""

    # 使用智谱 AI GLM-4 生成报告
    report = await call_llm(prompt, model="glm-4.7", temperature=0.7)

    logger.info(f"Report generated (length: {len(report)} chars)")

    # 返回更新
    return {
        "draft_report": report,
        "final_report": report if revision_count == 0 else state.get("final_report", ""),
        "revision_count": revision_count + 1,
    }


async def critic_node(state: AgentState) -> AgentState:
    """
    评审报告质量，决定是否需要重写

    输入:
        - target_position: 目标岗位
        - draft_report: 待评审的报告
        - revision_count: 当前修订次数

    输出:
        - critique: 评审意见（"APPROVED" 表示通过）
    """
    logger.info("Running critic_node...")

    # 构建 prompt
    prompt = CRITIC_CHECKLIST.format(target_position=state["target_position"])

    # 加入报告内容
    prompt += f"""
## 待评审的报告

{state.get("draft_report", "")}

请严格按照上述检查清单进行评审。
"""

    # 使用智谱 AI GLM-4 进行评审
    critique = await call_llm(prompt, model="glm-4.7", temperature=0.0)

    logger.info(f"Critic review completed. Result: {critique[:200]}...")

    return {"critique": critique}
