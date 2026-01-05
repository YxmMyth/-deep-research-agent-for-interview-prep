"""
测试智谱 AI GLM-4 API Key 是否有效
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from zhipuai import ZhipuAI

# 加载环境变量
load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

print(f"读取到的 API Key: {api_key[:20]}..." if api_key else "错误: 未找到 API Key")

if not api_key:
    print("\n错误: .env 文件中没有 ZHIPUAI_API_KEY")
    print("\n请在 .env 文件中添加:")
    print("ZHIPUAI_API_KEY=你的完整Key")
    sys.exit(1)

print(f"\n正在测试 API Key: {api_key[:10]}...{api_key[-10:]}")

try:
    print("\n调用智谱 AI GLM-4 API...")
    client = ZhipuAI(api_key=api_key)
    response = client.chat.completions.create(
        model="glm-4.7",
        messages=[
            {"role": "user", "content": "你好，请回复'测试成功'"}
        ],
        max_tokens=10,
    )

    print(f"\nAPI Key 有效！")
    print(f"模型回复: {response.choices[0].message.content}")

except Exception as e:
    print(f"\n发生错误: {str(e)}")
    print("\n可能的原因:")
    print("1. API Key 格式不正确")
    print("2. API Key 已过期或被禁用")
    print("3. 网络连接问题")
    print("4. API Key 还未激活（新创建的 Key 可能需要几分钟）")
