"""
Node 2: Researchers

并行执行两个任务：
- jd_researcher: 搜索并提取 JD
- interview_researcher: 搜索并提取面经
"""

import asyncio
import logging
import time
import os
from langchain_openai import ChatOpenAI
from src.state import AgentState
from src.tools.search import tavily_search
from src.tools.scraper import run_scraper_pipeline
from src.schemas import JobDescriptionSchema, InterviewLogSchema
from src.prompts.templates import JD_EXTRACTION_PROMPT, INTERVIEW_EXTRACTION_PROMPT
from src.progress_tracker import get_progress_tracker, AnalysisStage

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
        - analysis_mode: 分析模式 ("quick" 或 "standard")

    输出:
        - job_descriptions: JobDescriptionSchema 列表（累加到状态中）
    """
    logger.info("Running jd_researcher_node...")

    # 获取进度追踪器和分析模式
    tracker = get_progress_tracker()
    analysis_mode = state.get("analysis_mode", "standard")

    # 快速模式：每个查询返回 1 个 URL（标准模式：5 个）
    max_results = 1 if analysis_mode == "quick" else 5
    # 可通过环境变量降低抓取数量，便于快速跑通
    env_limit = os.getenv("SEARCH_MAX_RESULTS")
    if env_limit:
        try:
            max_results = max(1, min(max_results, int(env_limit)))
        except ValueError:
            pass
    logger.info(f"Analysis mode: {analysis_mode}, max_results per query: {max_results}")

    queries = state.get("jd_search_queries", [])
    all_jds = []

    # 计算总任务数（用于进度追踪）
    total_tasks = len(queries) * max_results
    completed_count = 0

    # 更新阶段
    tracker.update_stage(AnalysisStage.JD_RESEARCH)

    # 对每个查询进行搜索
    for query in queries:
        try:
            logger.info(f"Searching JDs with query: {query}")
            urls = tavily_search(query, max_results=max_results, search_depth="advanced")

            # 逐个处理 URL（串行）以准确报告进度
            for url in urls:
                completed_count += 1
                tracker.update_url_progress(url, completed_count, total_tasks, AnalysisStage.JD_RESEARCH)
                logger.info(f"Processing JD {completed_count}/{total_tasks}: {url}")

                start_time = time.time()
                try:
                    jd = await run_scraper_pipeline(url, JobDescriptionSchema, JD_EXTRACTION_PROMPT)
                    all_jds.append(jd)
                    logger.info(f"✅ Successfully extracted JD from {jd.company_name}")
                    tracker.record_extraction_result(success=True, duration=time.time() - start_time)
                except Exception as e:
                    logger.error(f"❌ Failed to extract JD from {url}: {e}")
                    tracker.record_extraction_result(success=False, duration=time.time() - start_time)

        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}")
            continue

    logger.info(f"JD researcher completed. Collected {len(all_jds)} JDs")

    # 更新阶段为完成
    tracker.update_stage(AnalysisStage.JD_RESEARCH_COMPLETE)

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
        - analysis_mode: 分析模式 ("quick" 或 "standard")

    输出:
        - interview_logs: InterviewLogSchema 列表（累加到状态中）
    """
    logger.info("Running interview_researcher_node...")

    # 获取进度追踪器和分析模式
    tracker = get_progress_tracker()
    analysis_mode = state.get("analysis_mode", "standard")

    # 快速模式：每个查询返回 1 个 URL（标准模式：5 个）
    max_results = 1 if analysis_mode == "quick" else 5
    # 可通过环境变量降低抓取数量，便于快速跑通
    env_limit = os.getenv("SEARCH_MAX_RESULTS")
    if env_limit:
        try:
            max_results = max(1, min(max_results, int(env_limit)))
        except ValueError:
            pass
    logger.info(f"Analysis mode: {analysis_mode}, max_results per query: {max_results}")

    queries = state.get("interview_search_queries", [])
    all_interviews = []

    # 计算总任务数（用于进度追踪）
    total_tasks = len(queries) * max_results
    completed_count = 0

    # 更新阶段
    tracker.update_stage(AnalysisStage.INTERVIEW_RESEARCH)

    # 对每个查询进行搜索
    for query in queries:
        try:
            logger.info(f"Searching interview logs with query: {query}")
            urls = tavily_search(query, max_results=max_results, search_depth="advanced")

            # 逐个处理 URL（串行）以准确报告进度
            for url in urls:
                completed_count += 1
                tracker.update_url_progress(url, completed_count, total_tasks, AnalysisStage.INTERVIEW_RESEARCH)
                logger.info(f"Processing interview {completed_count}/{total_tasks}: {url}")

                start_time = time.time()
                try:
                    interview = await run_scraper_pipeline(url, InterviewLogSchema, INTERVIEW_EXTRACTION_PROMPT)
                    all_interviews.append(interview)
                    logger.info(f"✅ Successfully extracted interview from {interview.company_name}")
                    tracker.record_extraction_result(success=True, duration=time.time() - start_time)
                except Exception as e:
                    logger.error(f"❌ Failed to extract interview from {url}: {e}")
                    tracker.record_extraction_result(success=False, duration=time.time() - start_time)

        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}")
            continue

    logger.info(f"Interview researcher completed. Collected {len(all_interviews)} interview logs")

    # 更新阶段为完成
    tracker.update_stage(AnalysisStage.INTERVIEW_RESEARCH_COMPLETE)

    # 返回累加的结果
    return {"interview_logs": all_interviews}
