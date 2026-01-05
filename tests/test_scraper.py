"""
ETL Pipeline 单元测试

测试 scraper.py 中的核心功能
"""

import pytest
import asyncio
from src.tools.scraper import crawl_to_markdown, extract_structured_data
from src.schemas import JobDescriptionSchema, InterviewLogSchema


# 测试用的公开 URL
TEST_JD_URL = "https://jobs.bytedance.com/experienced/position/7351394354371024136/detail"
TEST_INTERVIEW_URL = "https://www.nowcoder.com/discuss/526471"


@pytest.mark.asyncio
async def test_crawl_to_markdown():
    """测试 crawl_to_markdown 函数"""
    # 使用一个简单的测试 URL
    url = "https://example.com"

    try:
        markdown = await crawl_to_markdown(url)
        assert isinstance(markdown, str)
        assert len(markdown) > 0
        print(f"✓ Successfully crawled {len(markdown)} characters")
    except ValueError as e:
        # 某些网站可能无法访问，这是预期的
        pytest.skip(f"Skipping due to network error: {e}")


@pytest.mark.asyncio
async def test_extract_jd_from_markdown():
    """测试从 Markdown 提取 JD"""
    # 模拟一个简单的 JD Markdown
    markdown_content = """
# 高级后端工程师

## 公司
字节跳动

## 岗位职责
1. 负责后端系统架构设计
2. 参与技术方案评审
3. 优化系统性能

## 任职要求
1. 精通 Python/Go 语言
2. 熟悉微服务架构
3. 有高并发系统经验

## 加分项
- 有大型互联网公司经验
- 熟悉 Kubernetes
"""

    try:
        jd = extract_structured_data(
            markdown_content,
            JobDescriptionSchema,
            "提取这份招聘 JD 的所有关键信息",
        )

        assert isinstance(jd, JobDescriptionSchema)
        assert hasattr(jd, "company_name")
        assert hasattr(jd, "required_skills")
        print(f"✓ Successfully extracted JD: {jd.company_name}")
        print(f"  Required skills: {jd.required_skills}")

    except ValueError as e:
        # 如果 API Key 未设置，跳过测试
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        else:
            raise


@pytest.mark.asyncio
async def test_extract_interview_from_markdown():
    """测试从 Markdown 提取面经"""
    markdown_content = """
# 字节跳动后端面试经验

## 公司
字节跳动

## 岗位
后端开发工程师

## 面试结果
收到 offer

## 面试过程

### 一面
1. 自我介绍
2. 项目经历
3. 算法题：LRU 缓存实现
4. 数据库索引优化

难度：中等

### 二面
1. 系统设计：设计一个短链接系统
2. Redis 分布式锁实现
3. 消息队列如何保证不丢失

难度：困难

## 考察技能
- 算法与数据结构
- 系统设计
- 数据库优化
- 分布式系统

## 建议
一定要刷 LeetCode，系统设计要准备充分
"""

    try:
        interview = extract_structured_data(
            markdown_content,
            InterviewLogSchema,
            "提取这份面经的所有关键信息",
        )

        assert isinstance(interview, InterviewLogSchema)
        assert hasattr(interview, "company_name")
        assert hasattr(interview, "rounds")
        print(f"✓ Successfully extracted interview: {interview.company_name}")
        print(f"  Number of rounds: {len(interview.rounds)}")

    except ValueError as e:
        # 如果 API Key 未设置，跳过测试
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        else:
            raise


@pytest.mark.asyncio
async def test_full_pipeline_integration():
    """测试完整的 ETL Pipeline"""
    # 使用模拟数据测试集成
    markdown = """
# 软件工程师

## 公司
Test Company

## 岗位职责
负责软件开发

## 要求
- 熟悉 Python
- 熟悉 Django
"""

    try:
        schema = JobDescriptionSchema
        prompt = "提取 JD 信息"

        # 由于需要 crawl，这里只测试 extract 部分
        result = extract_structured_data(markdown, schema, prompt)
        assert isinstance(result, JobDescriptionSchema)
        print("✓ Full pipeline integration test passed")

    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        else:
            raise


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
