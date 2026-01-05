"""
测试脚本 - 自动输入示例简历
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

from src.graph import build_graph

# 加载环境变量
load_dotenv()

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

console = Console(force_terminal=True, legacy_windows=False)


async def main():
    """主函数"""
    # 打印欢迎信息
    console.print("\n[bold cyan]=== 测试模式 ===[/bold cyan]\n")

    # 检查环境变量
    required_vars = ["ZHIPUAI_API_KEY", "TAVILY_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        console.print(f"[red]错误: 缺少环境变量: {', '.join(missing_vars)}[/red]")
        sys.exit(1)

    # 读取示例简历
    resume_file = Path("example_resume.txt")
    if not resume_file.exists():
        console.print(f"[red]错误: 找不到 {resume_file}[/red]")
        sys.exit(1)

    resume_content = resume_file.read_text(encoding='utf-8')
    # 移除 END 标记
    resume_content = resume_content.replace("END", "").strip()

    console.print(f"[green]已读取简历 ({len(resume_content)} 字符)[/green]\n")

    # 目标岗位
    target_position = "字节跳动 后端开发 2026校招"

    console.print(f"[green]目标岗位: {target_position}[/green]\n")

    # 构建并运行 Graph
    console.print("[bold yellow]开始分析市场实情...[/bold yellow]\n")

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
            console.print("[cyan]Step 1: 生成研究计划...[/cyan]")
            final_state = await graph.ainvoke(initial_state)

        # 显示最终报告
        console.print("\n[bold green]分析完成！[/bold green]\n")

        # 使用 Markdown 渲染报告
        if final_state.get("final_report"):
            from rich.markdown import Markdown
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
