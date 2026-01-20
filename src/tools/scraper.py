"""
ETL Pipeline: URL -> Clean Markdown -> Structured JSON

数据流:
┌─────────┐     ┌───────────┐     ┌────────────────┐     ┌──────────────┐
│  URL    │ --> │ Crawl4AI  │ --> │ Clean Markdown │ --> │ Direct LLM   │ --> Pydantic Object
└─────────┘     │ (爬取+清洗)│     │ (无广告/导航)   │     │ (结构化提取)  │
                └───────────┘     └────────────────┘     └──────────────┘
"""

import os
import sys
import asyncio
import json
from crawl4ai import AsyncWebCrawler
from pydantic import BaseModel
from typing import TypeVar, Type
import logging
import io

from src.llm import call_llm_with_system_message

# Windows 编码修复（必须在所有其他导入之前）
if sys.platform == "win32":
    # 强制使用 UTF-8 编码
    os.environ["PYTHONIOENCODING"] = "utf-8"
    # 重新配置标准输出流使用 UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    else:
        # Python 3.9 及更早版本
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except OSError:
    # Some Streamlit runners replace stdio with objects that reject reconfigure.
    pass

# 配置 logger 使用安全的编码
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # 强制重新配置
)
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def crawl_to_markdown(url: str) -> str:
    """
    Step 1: 使用 Crawl4AI 将网页转为干净的 Markdown

    关键配置:
    - 启用 readability 模式去除广告
    - 移除 script/style 标签
    - 保留正文内容

    Args:
        url: 目标网页 URL

    Returns:
        清洗后的 Markdown 文本

    Raises:
        ValueError: 爬取失败时抛出异常
    """
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(
            url=url,
            word_count_threshold=10,  # 过滤短文本块
            remove_overlay_elements=True,  # 移除弹窗
            bypass_cache=True,  # 绕过缓存以确保最新数据
            timeout=30,  # 30秒超时，避免大网站爬取过久
            magic=True,  # 启用智能处理
        )

        if result.success:
            logger.info(f"Successfully crawled {url}, got {len(result.markdown)} chars")
            return result.markdown
        else:
            error_msg = f"Failed to crawl {url}: {result.error_message}"
            logger.error(error_msg)
            raise ValueError(error_msg)


async def extract_structured_data(
    markdown_content: str, schema: Type[T], extraction_prompt: str
) -> T:
    """
    Step 2: 使用阿里云通义千问从 Markdown 提取结构化数据

    Args:
        markdown_content: 清洗后的 Markdown 文本
        schema: 目标 Pydantic 模型类型
        extraction_prompt: 提取指令

    Returns:
        验证后的 Pydantic 对象

    Raises:
        ValueError: 提取或验证失败时抛出异常
    """
    # 构建 schema JSON
    schema_json = json.dumps(schema.model_json_schema(), indent=2, ensure_ascii=False)

    # 构建系统提示
    system_prompt = """你是一个专业的信息提取专家。你的任务是从文本中提取结构化数据。

请严格遵循提供的 JSON Schema 格式输出数据。
重要：
1. 必须严格遵循 Schema
2. 所有必需字段都必须有值
3. 列表字段如果没有内容则为空数组 []
4. 字符串字段如果无法提取则为 null 或空字符串
5. 只输出 JSON，不要包含其他解释性文字
"""

    # 构建用户提示
    user_prompt = f"""{extraction_prompt}

JSON Schema:
{schema_json}

请从以下文本中提取信息：

{markdown_content[:10000]}

请严格按照上述 Schema 输出 JSON 格式。
"""

    try:
        logger.info("Running LLM extraction...")

        # 使用智谱 AI GLM-4 API
        response_content = await call_llm_with_system_message(
            system_message=system_prompt,
            user_message=user_prompt,
            model="glm-4.7",
            temperature=0.0,
        )

        # 提取 JSON 部分（处理可能的 markdown 代码块）
        content = response_content
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.rfind("```")
            content = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.rfind("```")
            content = content[json_start:json_end].strip()

        # 解析 JSON
        extracted_data = json.loads(content)

        # 验证并转换为 Pydantic 对象
        validated_obj = schema.model_validate(extracted_data)
        logger.info(f"Successfully extracted and validated data: {type(schema).__name__}")

        return validated_obj

    except Exception as e:
        error_msg = f"Failed to extract structured data: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


async def run_scraper_pipeline(
    url: str, schema: Type[T], extraction_prompt: str
) -> T:
    """
    完整 ETL Pipeline: URL -> Pydantic Object

    Args:
        url: 目标网页 URL
        schema: 目标 Pydantic 模型类型
        extraction_prompt: 提取指令

    Returns:
        包含 source_url 的验证后 Pydantic 对象

    Raises:
        ValueError: 爬取或提取失败时抛出异常

    Example:
        >>> from src.schemas import JobDescriptionSchema
        >>> jd = await run_scraper_pipeline(
        ...     url="https://jobs.bytedance.com/...",
        ...     schema=JobDescriptionSchema,
        ...     extraction_prompt="提取这份招聘 JD 的所有关键信息"
        ... )
        >>> print(jd.company_name)
    """
    logger.info(f"Starting ETL pipeline for {url}")

    # Step 1: Crawl + Clean
    markdown = await crawl_to_markdown(url)

    # 检查内容长度（跳过空内容或太短的页面）
    if len(markdown.strip()) < 50:
        error_msg = f"Content too short ({len(markdown)} chars), skipping"
        logger.warning(error_msg)
        raise ValueError(error_msg)

    # Step 2: Extract + Validate
    structured_data = await extract_structured_data(markdown, schema, extraction_prompt)

    # 附加来源 URL
    if hasattr(structured_data, "source_url"):
        structured_data.source_url = url

    logger.info(f"ETL pipeline completed successfully for {url}")
    return structured_data
