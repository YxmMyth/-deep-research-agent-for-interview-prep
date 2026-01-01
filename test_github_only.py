"""
测试 GitHub 工具（不需要其他 API Keys）
"""

import sys
import io

# 设置 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.tools.github_tool import get_github_stats
import json

print("="*60)
print("Testing GitHub Stats Tool")
print("="*60)

# 测试 1: 搜索知名公司的 GitHub 组织
test_companies = ["DeepSeek", "google", "microsoft"]

for company in test_companies:
    print(f"\nAnalyzing company: {company}")
    print("-"*60)

    try:
        result = get_github_stats(company, top_n=3)

        if result.get("error"):
            print(f"Error: {result['error']}")
        else:
            print(f"Organization: {result['organization']}")
            print(f"Total repositories: {result['total_repositories']}")
            print(f"\nLanguage distribution:")
            for lang in result['language_distribution']:
                print(f"   - {lang['language']}: {lang['percentage']}%")

            print(f"\nTop 3 repositories:")
            for i, repo in enumerate(result['top_repos'], 1):
                print(f"   {i}. {repo['name']} (Stars: {repo['stars']}, Language: {repo['language']})")

            # 显示 ECharts 配置
            if result.get('echarts_config'):
                print(f"\nECharts config generated (length: {len(result['echarts_config'])} chars)")
                print("First 100 chars:")
                print(result['echarts_config'][:100] + "...")

    except Exception as e:
        print(f"Execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Test completed")
print("="*60)
