"""
主入口文件
可以直接运行此文件来启动 Agent
"""

import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from src.graph import run_research_agent


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py <公司名称> [额外查询]")
        print("示例: python main.py DeepSeek")
        print("示例: python main.py ByteDance '重点关注前端技术栈'")
        sys.exit(1)

    company_name = sys.argv[1]
    user_query = sys.argv[2] if len(sys.argv) > 2 else ""

    # 运行 Agent
    try:
        result = run_research_agent(company_name, user_query)

        # 保存报告
        report = result.get("final_report", "")
        if report:
            filename = f"{company_name}_report.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\nReport saved to: {filename}")

            # 询问是否打开
            try:
                input("\nPress Enter to exit...")
            except KeyboardInterrupt:
                pass
        else:
            print("\nReport generation failed")
            sys.exit(1)

    except Exception as e:
        print(f"\nExecution Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
