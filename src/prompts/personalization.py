"""
个性化提示词生成器

根据用户画像动态调整提示词，提供更贴合用户需求的报告
"""

from src.schemas import UserProfile


def get_personalized_prompts(user_profile: UserProfile, base_prompt: str) -> str:
    """
    根据用户画像动态调整提示词

    调整维度：
    1. 技术深度（初级 vs 高级）
    2. 解释详细程度
    3. 学习资源类型偏好
    4. 时间规划紧迫度

    Args:
        user_profile: 用户画像
        base_prompt: 基础提示词模板

    Returns:
        个性化调整后的提示词
    """

    # 经验水平修饰符
    depth_modifiers = {
        "junior": """
## 面向初级开发者
- 用通俗易懂的语言解释每个技术点
- 提供详细的背景知识和学习路径
- 推荐入门级教程和官方文档
- 避免过于深入的理论和底层实现
- 重点讲解"是什么"和"怎么用"
""",
        "mid": """
## 面向中级开发者
- 平衡理论深度和实战建议
- 重点讲解常见面试考察点
- 推荐进阶学习资源和实战项目
- 适当深入底层原理，但不至于过深
- 重点讲解"为什么"和"最佳实践"
""",
        "senior": """
## 面向高级开发者
- 深入探讨架构设计、系统设计
- 重点讲解技术选型、权衡和最佳实践
- 推荐深度技术资源、源码分析、论文
- 关注性能优化、可扩展性、可维护性
- 重点讲解"设计思路"和"技术决策"
"""
    }

    # 学习风格修饰符
    style_modifiers = {
        "visual": """
## 视觉化学习风格
- 多使用图表、架构图、流程图、时序图等视觉化方式呈现
- 推荐视频教程、可视化工具、图解文档
- 用直观的示例说明抽象概念
""",
        "practical": """
## 实战导向学习风格
- 重点推荐实战项目、动手练习、代码示例
- 提供可直接运行的示例代码
- 强调动手实践和实验性学习
- 推荐编程练习平台、开源项目参与机会
""",
        "theoretical": """
## 理论导向学习风格
- 推荐书籍、论文、技术文档等深度资源
- 详细讲解理论背景和原理
- 提供数学证明和公式推导（如适用）
- 关注学术前沿和技术演进历史
"""
    }

    # 时间紧迫度修饰符
    time_modifiers = ""
    if user_profile.preparation_time_weeks <= 2:
        time_modifiers = """
## 时间紧迫提醒
用户准备时间较短（≤2周），请：
- 优先列出最高频、最核心的考察点
- 精简学习资源，只保留最必要的 2-3 个
- 提供突击学习策略和速成建议
- 明确标注"必须掌握"vs"可选了解"
"""
    elif user_profile.preparation_time_weeks >= 8:
        time_modifiers = """
## 充裕准备时间
用户准备时间较充裕（≥8周），请：
- 提供系统的学习路径和阶段性目标
- 推荐更全面的学习资源和深度内容
- 建议长期项目积累和技能提升计划
- 可以包含一些拓展性学习内容
"""

    # 组合所有修饰符
    profile_context = f"""{depth_modifiers[user_profile.experience_level]}
{style_modifiers[user_profile.learning_style]}
{time_modifiers}
"""

    # 注入到基础提示词
    # 在提示词的开头插入用户画像上下文
    if "## 报告要求" in base_prompt:
        # 标准格式：在"## 报告要求"之前插入
        return base_prompt.replace("## 报告要求", f"{profile_context}## 报告要求")
    elif "# 报告要求" in base_prompt:
        # 备用格式
        return base_prompt.replace("# 报告要求", f"{profile_context}# 报告要求")
    else:
        # 如果找不到标准标记，直接在开头插入
        return f"{profile_context}\n\n{base_prompt}"


def get_urgent_mode_prompt(base_prompt: str) -> str:
    """
    生成紧急模式的提示词（准备时间≤2周）

    Args:
        base_prompt: 基础提示词

    Returns:
        紧急模式调整后的提示词
    """
    urgent_instruction = """
## 紧急模式 - 核心优先

用户准备时间极其紧迫，请严格遵循以下原则：
1. 只列出 HIGH 优先级的差距
2. 每个差距只提供 1-2 个最核心的学习资源
3. 时间规划精确到天
4. 省略所有"nice-to-have"的内容
5. 强调最可能考察的核心知识点
"""

    if "## 报告要求" in base_prompt:
        return base_prompt.replace("## 报告要求", f"{urgent_instruction}\n\n## 报告要求")
    else:
        return f"{urgent_instruction}\n\n{base_prompt}"
