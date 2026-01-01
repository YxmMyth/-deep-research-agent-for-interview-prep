"""
Reporter Node - 报告生成节点
生成最终的 Markdown 报告
"""

from typing import Dict, Any
from datetime import datetime
import json

from ..state import AgentState


def reporter_node(state: AgentState) -> Dict[str, Any]:
    """
    报告节点：生成最终的 Markdown 报告

    逻辑：
    1. 汇总所有数据和分析结果
    2. 生成结构化的 Markdown 报告
    3. 如果有技术栈数据，嵌入 ECharts 代码

    Args:
        state: 当前状态

    Returns:
        状态更新字典（包含 final_report）
    """
    print("\n[Reporter Node] Generating report...")

    company_name = state["company_name"]

    # 生成报告
    report = _generate_markdown_report(state)

    updates = {
        "final_report": report,
        "current_step": "completed"
    }

    print("  [OK] Report generated")

    return updates


def _generate_markdown_report(state: AgentState) -> str:
    """
    生成 Markdown 格式的报告

    Args:
        state: 当前状态

    Returns:
        Markdown 报告文本
    """
    company_name = state["company_name"]
    current_date = datetime.now().strftime("%Y-%m-%d")

    # 报告头部
    md_lines = [
        f"# {company_name} 求职备战深度调研报告",
        "",
        f"**生成时间**: {current_date}",
        f"**数据来源**: GitHub, Tavily Search",
        "",
        "---",
        "",
    ]

    # 1. 公司概览
    md_lines.extend([
        "## 📊 公司概览",
        ""
    ])

    if state.get("company_info"):
        info = state["company_info"]
        md_lines.append(f"**描述**: {info.get('description', '暂无描述')}")
        md_lines.append(f"**行业**: {info.get('industry', '未知')}")
        md_lines.append("")

    # 2. 技术栈分析（核心部分）
    if state.get("github_stats"):
        md_lines.extend([
            "## 💻 技术栈分析",
            ""
        ])

        stats = state["github_stats"]
        md_lines.append(f"**GitHub 组织**: [{stats['organization']}](https://github.com/{stats['organization']})")
        md_lines.append(f"**开源仓库总数**: {stats['total_repositories']}")
        md_lines.append("")

        # 语言分布表格
        md_lines.extend([
            "### 编程语言分布",
            "",
            "| 语言 | 占比 | 仓库数 |",
            "|------|------|--------|"
        ])

        for lang in stats.get("language_distribution", []):
            md_lines.append(
                f"| {lang['language']} | {lang['percentage']}% | {lang['repository_count']} |"
            )

        md_lines.append("")

        # Top 仓库
        md_lines.extend([
            "### 🔥 热门开源项目",
            ""
        ])

        for i, repo in enumerate(stats.get("top_repos", []), 1):
            md_lines.extend([
                f"{i}. **[{repo['name']}]({repo['url']})**",
                f"   - ⭐ Stars: {repo['stars']}",
                f"   - 🏷️ 语言: {repo['language']}",
                f"   - 📝 描述: {repo['description'] or '无描述'}",
                ""
            ])

        # ECharts 可视化代码
        if stats.get("echarts_config"):
            md_lines.extend([
                "### 📈 技术栈可视化",
                "",
                "```json",
                stats["echarts_config"],
                "```",
                ""
            ])

        md_lines.extend([
            "---",
            ""
        ])

    # 3. 最新动态
    if state.get("news_articles"):
        md_lines.extend([
            "## 📰 最新动态",
            ""
        ])

        for article in state["news_articles"][:5]:
            md_lines.extend([
                f"- **[{article['title']}]({article['url']})**",
                f"  {article['summary'][:200]}...",
                ""
            ])

        md_lines.extend([
            "---",
            ""
        ])

    # 4. 面试经验
    if state.get("interview_experiences"):
        md_lines.extend([
            "## 🎯 面试经验汇总",
            ""
        ])

        for exp in state["interview_experiences"][:3]:
            md_lines.extend([
                f"### {exp['title']}",
                "",
                exp['content'][:500] + "...",
                "",
                f"来源: {exp['source']}",
                ""
            ])

        md_lines.extend([
            "---",
            ""
        ])

    # 5. 深度分析
    if state.get("analysis_summary"):
        md_lines.extend([
            "## 🔬 深度分析",
            "",
            state["analysis_summary"],
            "",
            "---",
            ""
        ])

    # 6. 关键洞察与建议
    if state.get("key_insights"):
        md_lines.extend([
            "## 💡 关键洞察与建议",
            ""
        ])

        for i, insight in enumerate(state["key_insights"], 1):
            md_lines.append(f"{i}. {insight}")

        md_lines.extend([
            "",
            "---",
            ""
        ])

    # 7. 准备建议
    md_lines.extend([
        "## 📚 建议准备方向",
        "",
        "基于以上分析，建议从以下维度准备：",
        "",
    ])

    # 根据技术栈添加建议
    if state.get("github_stats"):
        langs = state["github_stats"].get("language_distribution", [])
        if langs:
            top_3_langs = [lang["language"] for lang in langs[:3]]
            md_lines.append(f"1. **技术栈**: 重点准备 {', '.join(top_3_langs)}")

    md_lines.extend([
        "2. **项目经验**: 复习 Top 仓库的技术实现",
        "3. **面试题**: 参考上述面试经验，针对性准备",
        "",
        "---",
        "",
    ])

    # 报告尾部
    md_lines.extend([
        "## 📝 附录",
        "",
        f"- **数据检索日期**: {current_date}",
        f"- **分析工具**: Deep Research Agent v1.0",
        "",
        "---",
        "",
        "*本报告由 AI 自动生成，仅供参考。建议结合官方渠道获取最新信息。*"
    ])

    return "\n".join(md_lines)
