"""
Market-Reality Aligned Interview Agent

CLI 入口程序
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

from src.graph import build_graph

# 加载环境变量
load_dotenv()

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == "win32":
    import locale
    try:
        # 尝试设置控制台编码为 UTF-8
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

console = Console(force_terminal=True, legacy_windows=False)


def check_env_vars():
    """检查必需的环境变量"""
    required_vars = ["ZHIPUAI_API_KEY", "TAVILY_API_KEY"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        console.print(
            f"[red]错误: 缺少必需的环境变量: {', '.join(missing_vars)}[/red]"
        )
        console.print("\n请创建 .env 文件并设置以下变量：")
        console.print("  - ZHIPUAI_API_KEY=你的完整Key")
        console.print("  - TAVILY_API_KEY=tvly-...")
        console.print("\n参考 .env.example 文件\n")
        sys.exit(1)


async def main():
    """主函数"""
    # 打印欢迎信息
    console.print(
        Panel(
            "[bold blue]Market-Reality Aligned Interview Agent[/bold blue]\n\n"
            "对比官方 JD 与民间面经，发现你的技能 Gap",
            title="[bold green]求职备战助手[/bold green]",
            border_style="blue",
        )
    )

    # 检查环境变量
    check_env_vars()

    # 获取用户输入
    console.print("\n[bold yellow]第一步: 请提供你的简历内容[/bold yellow]")
    console.print("提示: 粘贴完整简历后，在新的一行输入 END 并回车\n")

    resume_lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        resume_lines.append(line)

    resume_content = "\n".join(resume_lines)

    if not resume_content.strip():
        console.print("[red]错误: 简历内容不能为空[/red]")
        sys.exit(1)

    console.print(f"\n[green]已接收简历内容 ({len(resume_content)} 字符)[/green]")

    # 获取目标岗位
    target_position = Prompt.ask(
        "\n[bold yellow]第二步: 请输入目标岗位[/bold yellow]",
        default="字节跳动 后端开发 2026校招",
    )

    # 确保 target_position 是有效的 UTF-8
    if isinstance(target_position, str):
        target_position = target_position.encode('utf-8', errors='ignore').decode('utf-8')

    console.print(f"\n[green]目标岗位: {target_position}[/green]")

    # 构建并运行 Graph
    console.print("\n[bold yellow]第三步: 开始分析市场实情...[/bold yellow]\n")

    try:
        graph = build_graph()

        initial_state = {
            "resume_content": resume_content,
            "target_position": target_position,
            "job_descriptions": [],
            "interview_logs": [],
            "revision_count": 0,
        }

        with console.status("[bold cyan]正在分析中，请稍候...[/bold cyan]") as status:
            # 更新状态信息
            status.update("[bold cyan]Step 1: 生成研究计划...[/bold cyan]")
            final_state = await graph.ainvoke(initial_state)

        # 显示最终报告
        console.print("\n[bold green]分析完成！[/bold green]\n")

        # 使用 Markdown 渲染报告
        if final_state.get("final_report"):
            markdown = Markdown(final_state["final_report"])
            console.print(markdown)

        # 保存报告到文件
        output_file = Path("interview_preparation_report.md")
        output_file.write_text(final_state.get("final_report", ""), encoding="utf-8")
        console.print(f"\n[blue]报告已保存至: {output_file.absolute()}[/blue]")

    except Exception as e:
        console.print(f"\n[red]错误: {str(e)}[/red]")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]用户中断[/yellow]")
        sys.exit(0)
