"""
Node 2: Researchers

并行执行两个任务：
- jd_researcher: 搜索并提取 JD
- interview_researcher: 搜索并提取面经
"""

import asyncio
import logging
from langchain_openai import ChatOpenAI
from src.state import AgentState
from src.tools.search import tavily_search
from src.tools.scraper import run_scraper_pipeline
from src.schemas import JobDescriptionSchema, InterviewLogSchema
from src.prompts.templates import JD_EXTRACTION_PROMPT, INTERVIEW_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


async def jd_researcher_node(state: AgentState) -> AgentState:
    """
    Worker A: 搜索 JD 并提取结构化数据

    流程:
    1. 根据搜索关键词获取 URL 列表
    2. 并行爬取和提取每个 URL 的 JD
    3. 返回提取到的 JobDescriptionSchema 列表

    输入:
        - jd_search_queries: JD 搜索关键词列表

    输出:
        - job_descriptions: JobDescriptionSchema 列表（累加到状态中）
    """
    logger.info("Running jd_researcher_node...")

    queries = state.get("jd_search_queries", [])
    all_jds = []

    # 对每个查询进行搜索
    for query in queries:
        try:
            logger.info(f"Searching JDs with query: {query}")
            urls = tavily_search(query, max_results=5, search_depth="advanced")

            # 并行处理所有 URL
            tasks = [
                run_scraper_pipeline(url, JobDescriptionSchema, JD_EXTRACTION_PROMPT)
                for url in urls
            ]
            jds = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤成功的提取结果
            for jd in jds:
                if isinstance(jd, Exception):
                    logger.error(f"Failed to extract JD: {jd}")
                elif isinstance(jd, JobDescriptionSchema):
                    all_jds.append(jd)
                    logger.info(f"Successfully extracted JD from {jd.company_name}")

        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}")
            continue

    logger.info(f"JD researcher completed. Collected {len(all_jds)} JDs")

    # 返回累加的结果
    return {"job_descriptions": all_jds}


async def interview_researcher_node(state: AgentState) -> AgentState:
    """
    Worker B: 搜索面经并提取结构化数据

    流程:
    1. 根据搜索关键词获取 URL 列表
    2. 并行爬取和提取每个 URL 的面经
    3. 返回提取到的 InterviewLogSchema 列表

    输入:
        - interview_search_queries: 面经搜索关键词列表

    输出:
        - interview_logs: InterviewLogSchema 列表（累加到状态中）
    """
    logger.info("Running interview_researcher_node...")

    queries = state.get("interview_search_queries", [])
    all_interviews = []

    # 对每个查询进行搜索
    for query in queries:
        try:
            logger.info(f"Searching interview logs with query: {query}")
            urls = tavily_search(query, max_results=5, search_depth="advanced")

            # 并行处理所有 URL
            tasks = [
                run_scraper_pipeline(url, InterviewLogSchema, INTERVIEW_EXTRACTION_PROMPT)
                for url in urls
            ]
            interviews = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤成功的提取结果
            for interview in interviews:
                if isinstance(interview, Exception):
                    logger.error(f"Failed to extract interview: {interview}")
                elif isinstance(interview, InterviewLogSchema):
                    all_interviews.append(interview)
                    logger.info(
                        f"Successfully extracted interview from {interview.company_name}"
                    )

        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}")
            continue

    logger.info(f"Interview researcher completed. Collected {len(all_interviews)} interview logs")

    # 返回累加的结果
    return {"interview_logs": all_interviews}
