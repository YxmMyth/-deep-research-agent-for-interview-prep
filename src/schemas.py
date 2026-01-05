"""
Core Pydantic data models for the Interview Agent

所有数据模型定义在此，作为 ScrapeGraphAI 的提取目标
"""

from pydantic import BaseModel, Field
from typing import Optional


# ===== 输入模型 =====
class AgentInput(BaseModel):
    """Agent 启动时的用户输入"""

    resume_content: str = Field(..., description="用户简历全文本")
    target_position: str = Field(..., description="目标岗位，如: 字节跳动 后端开发 2026校招")


# ===== JD 提取目标 =====
class JobDescriptionSchema(BaseModel):
    """从招聘网站提取的结构化 JD"""

    company_name: str = Field(..., description="公司名称")
    position_title: str = Field(..., description="职位名称")
    required_skills: list[str] = Field(default_factory=list, description="明确要求的技能列表")
    preferred_skills: list[str] = Field(default_factory=list, description="加分项技能")
    education_requirement: Optional[str] = Field(None, description="学历要求")
    experience_requirement: Optional[str] = Field(None, description="经验要求")
    salary_range: Optional[str] = Field(None, description="薪资范围")
    job_responsibilities: list[str] = Field(default_factory=list, description="岗位职责")
    source_url: str = Field(..., description="数据来源 URL")


# ===== 面经提取目标 =====
class InterviewRound(BaseModel):
    """单轮面试记录"""

    round_name: str = Field(..., description="面试轮次，如: 一面/二面/HR面")
    questions: list[str] = Field(default_factory=list, description="被问到的问题列表")
    difficulty: Optional[str] = Field(None, description="难度评价")


class InterviewLogSchema(BaseModel):
    """从论坛/牛客网提取的面经"""

    company_name: str = Field(..., description="公司名称")
    position_title: str = Field(..., description="面试岗位")
    interview_date: Optional[str] = Field(None, description="面试时间")
    overall_result: Optional[str] = Field(None, description="最终结果: offer/拒绝/等待")
    rounds: list[InterviewRound] = Field(default_factory=list, description="各轮面试详情")
    key_skills_tested: list[str] = Field(default_factory=list, description="实际考察的技能点")
    tips: Optional[str] = Field(None, description="作者给出的建议")
    source_url: str = Field(..., description="数据来源 URL")


# ===== Gap 分析结果 =====
class SkillGap(BaseModel):
    """技能差距"""

    skill_name: str
    gap_type: str = Field(
        ...,
        description="missing_in_resume / jd_hidden_requirement / practical_weakness",
    )
    evidence: str = Field(..., description="支撑此结论的具体证据，必须引用 JD 或面经原文")
    priority: str = Field(..., description="high / medium / low")


class GapAnalysisResult(BaseModel):
    """三重对比分析结果"""

    resume_vs_jd: list[SkillGap] = Field(
        default_factory=list, description="简历 vs JD 的差距"
    )
    jd_vs_interview: list[SkillGap] = Field(
        default_factory=list, description="JD 未写但面试必考的技能"
    )
    resume_vs_interview: list[SkillGap] = Field(
        default_factory=list, description="简历中缺失的实战经验"
    )
