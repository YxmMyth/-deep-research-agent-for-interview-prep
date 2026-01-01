"""
Analyst Node - 分析节点
汇总、清洗和分析所有收集的数据
"""

from typing import Dict, Any, List
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState


def analyst_node(state: AgentState) -> Dict[str, Any]:
    """
    分析节点：汇总所有数据，生成深度分析

    逻辑：
    1. 汇总所有收集的数据
    2. 清洗和去重
    3. 使用 LLM 生成分析摘要
    4. 提取关键洞察

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    print("\n[Analyst Node] Analyzing data...")

    company_name = state["company_name"]

    # 1. 汇总数据
    summary_parts = []

    # GitHub 技术栈
    if state.get("github_stats"):
        stats = state["github_stats"]
        lang_dist = stats.get("language_distribution", [])
        lang_summary = ", ".join([
            f"{lang['language']} ({lang['percentage']}%)"
            for lang in lang_dist[:5]
        ])
        summary_parts.append(f"""
## Tech Stack Analysis

- Organization: {stats['organization']}
- Total Repositories: {stats['total_repositories']}
- Main Languages: {lang_summary}
- Top Repos:
""")
        for repo in stats.get("top_repos", [])[:3]:
            summary_parts.append(f"  - [{repo['name']}]({repo['url']}) (Stars: {repo['stars']}, Language: {repo['language']})")

    # 新闻动态
    if state.get("news_articles"):
        summary_parts.append(f"""
## Latest News

Got {len(state['news_articles'])} news articles:
""")
        for article in state["news_articles"][:3]:
            summary_parts.append(f"- [{article['title']}]({article['url']})")

    # 面试经验
    if state.get("interview_experiences"):
        summary_parts.append(f"""
## Interview Experiences Summary

Got {len(state['interview_experiences'])} interview experiences:
""")
        for exp in state["interview_experiences"][:2]:
            summary_parts.append(f"- {exp['title']}")

    # 2. 使用 LLM 生成深度分析
    analysis_summary = _generate_llm_analysis(state)
    key_insights = _extract_key_insights(state)

    updates = {
        "analysis_summary": analysis_summary,
        "key_insights": key_insights,
        "current_step": "analysis_completed"
    }

    print("  [OK] Analysis completed")

    return updates


def _generate_llm_analysis(state: AgentState) -> str:
    """
    使用 LLM 生成深度分析

    Args:
        state: 当前状态

    Returns:
        分析摘要文本
    """
    # 构建 prompt
    prompt = f"""
你是一位资深的行业分析师。请基于以下数据，对 {state['company_name']} 进行深度分析：

## GitHub 技术栈数据
{state.get('github_stats', '无数据')}

## 公司新闻
{len(state.get('news_articles', []))} 条新闻

## 面试经验
{len(state.get('interview_experiences', []))} 条面试经验

请从以下维度进行分析：
1. 技术栈特点（主要语言、工程能力）
2. 公司业务方向（基于新闻和仓库）
3. 面试重点（基于面经）
4. 建议准备方向

输出格式：Markdown，简洁专业。
"""

    try:
        # 尝试使用 OpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        # 如果 OpenAI 失败，尝试 Anthropic
        try:
            llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0.3)
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e2:
            # 如果都失败，返回基础分析
            return f"""
# {state['company_name']} 分析报告

## 技术栈
{state.get('github_stats', {}).get('language_distribution', '无数据')}

## 注意事项
LLM 分析失败，请检查 API 配置。
错误: {str(e2)}
"""


def _extract_key_insights(state: AgentState) -> List[str]:
    """
    提取关键洞察

    Args:
        state: 当前状态

    Returns:
        洞察列表
    """
    insights = []

    # 技术栈洞察
    if state.get("github_stats"):
        langs = state["github_stats"].get("language_distribution", [])
        if langs:
            top_lang = langs[0]["language"]
            insights.append(f"主要技术栈为 {top_lang}，建议重点准备相关知识")

    # 仓库洞察
    if state.get("github_stats"):
        repo_count = state["github_stats"]["total_repositories"]
        if repo_count > 50:
            insights.append(f"开源活跃度高（{repo_count} 个仓库），重视工程实践")

    # 面试洞察
    if state.get("interview_experiences"):
        insights.append(f"有 {len(state['interview_experiences'])} 条面经可供参考")

    return insights
