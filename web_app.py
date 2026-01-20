"""
Market-Reality Aligned Interview Agent - Streamlit Web App

网页版面试准备助手
"""

import asyncio
import os
import sys
import concurrent.futures
import threading
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv
import io
import json
import time
import uuid
import logging

# Windows 编码和 asyncio 修复（必须在其他导入之前）
if sys.platform == "win32":
    # 强制使用 UTF-8 编码
    os.environ["PYTHONIOENCODING"] = "utf-8"
    # 配置日志文件（解决 emoji 编码问题）
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('streamlit_debug.log', encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True
    )

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

    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        # 如果 WindowsProactorEventLoopPolicy 不可用，使用默认策略
        pass

import streamlit as st
from streamlit import status

from src.graph import build_graph
from src.utils.pdf_parser import extract_text_from_file
from src.rate_limiter import check_rate_limit, get_usage_stats
from src.progress_tracker import get_progress_tracker, AnalysisStage

# Ensure logs are written even if Streamlit overrides logging config.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('streamlit_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)

# 加载环境变量
load_dotenv()

# 设置页面配置
st.set_page_config(
    page_title="面试准备助手",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

STATUS_FILE = Path(".analysis_status.json")


def _read_status_file():
    if not STATUS_FILE.exists():
        return None
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_status_file(payload: dict) -> None:
    try:
        STATUS_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _clear_status_file() -> None:
    try:
        STATUS_FILE.unlink()
    except Exception:
        pass


def _restore_status_into_session() -> None:
    status = _read_status_file()
    if not status:
        return

    status_state = status.get("status")
    if status_state == "running":
        st.session_state.analysis_running = True
        st.session_state.analysis_status_msg = status.get(
            "message", "⏳ 任务在后台运行中..."
        )
        st.session_state.analysis_run_id = status.get("run_id", "")
        return

    if status_state == "error":
        st.session_state.analysis_running = False
        st.session_state.analysis_error = status.get("error", "分析失败")
        st.session_state.analysis_status_msg = f"❌ 分析失败: {st.session_state.analysis_error}"
        return

    if status_state == "success":
        report = status.get("final_report")
        if not report:
            report_path = Path("interview_preparation_report.md")
            if report_path.exists():
                report = report_path.read_text(encoding="utf-8")
        if report:
            st.session_state.result = {"final_report": report}
            st.session_state.analysis_done = True
            st.session_state.analysis_running = False
            st.session_state.analysis_status_msg = "✅ 分析完成！"


def _start_progress_heartbeat(run_id: str, stop_event: threading.Event) -> None:
    def _heartbeat():
        while not stop_event.is_set():
            state = get_progress_tracker().get_state()
            _write_status_file(
                {
                    "run_id": run_id,
                    "status": "running",
                    "message": state.current_stage_display,
                    "progress_percent": state.progress_percent,
                    "completed_tasks": state.completed_tasks,
                    "total_tasks": state.total_tasks,
                    "current_url": state.current_url,
                    "updated_at": time.time(),
                }
            )
            stop_event.wait(2)

    threading.Thread(target=_heartbeat, daemon=True).start()


def check_env_vars():
    """检查必需的环境变量"""
    required_vars = ["ZHIPUAI_API_KEY", "TAVILY_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        # 检测是否在Hugging Face Spaces环境
        is_huggingface = os.getenv("SPACE_ID") is not None

        if is_huggingface:
            st.error("❌ **应用配置错误**")
            st.warning("""
            管理员需要在Hugging Face Spaces的 **Settings → Secrets** 中配置以下环境变量：

            - `ZHIPUAI_API_KEY` - 智谱AI的API密钥
            - `TAVILY_API_KEY` - Tavily搜索的API密钥

            [前往设置页面](./settings)
            """)
        else:
            st.error(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
            st.info("**本地运行配置步骤：**")
            st.code("""
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 文件，填入你的API密钥：
ZHIPUAI_API_KEY=你的完整Key
TAVILY_API_KEY=tvly-...
            """)
            st.markdown("""
            **获取API密钥：**
            - 智谱AI: https://open.bigmodel.cn/
            - Tavily: https://tavily.com/
            """)

        return False

    return True


def run_analysis(resume_content: str, target_position: str, analysis_mode: str = "standard") -> dict:
    """
    运行分析流程（使用线程池避免 asyncio 嵌套问题）

    注意：这是阻塞版本，只应在后台线程中调用

    Args:
        resume_content: 简历内容
        target_position: 目标岗位
        analysis_mode: 分析模式 ("quick" 或 "standard")

    Returns:
        分析最终状态 (final_state)
    """
    import logging
    import asyncio
    logger = logging.getLogger(__name__)

    logger.info("🔧 run_analysis() called")
    logger.info(f"   - Creating new event loop in thread: {threading.current_thread().name}")

    async def analysis_async():
        try:
            logger.info("📋 Building graph...")
            graph = build_graph()

            initial_state = {
                "resume_content": resume_content,
                "target_position": target_position,
                "analysis_mode": analysis_mode,
                "job_descriptions": [],
                "interview_logs": [],
                "revision_count": 0,
            }

            logger.info("🚀 Starting graph.ainvoke()...")
            logger.info(f"   - Initial state keys: {list(initial_state.keys())}")

            # 使用 ainvoke 运行工作流
            final_state = await graph.ainvoke(initial_state)

            logger.info("✅ graph.ainvoke() completed")
            logger.info(f"   - Final state keys: {list(final_state.keys())}")
            return final_state

        except Exception as e:
            logger.error(f"❌ Analysis async failed: {e}", exc_info=True)
            raise

    # 在后台线程中直接运行异步流程
    logger.info("🔄 Running async analysis in background thread...")
    result = asyncio.run(analysis_async())
    logger.info("✅ run_analysis() returning result")
    return result


# 全局线程池执行器（用于后台任务）
_background_executor = None


def get_background_executor():
    """获取或创建后台线程池执行器"""
    global _background_executor
    if _background_executor is None:
        _background_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    return _background_executor


def get_node_display_name(node_name: str) -> str:
    """获取节点的显示名称"""
    display_names = {
        "planner": "📋 生成搜索计划",
        "jd_researcher": "🔍 搜索职位描述 (JD)",
        "interview_researcher": "🔍 搜索面试经验",
        "gap_analyst": "📊 分析技能差距",
        "report_writer": "✍️ 生成备战报告",
        "critic": "🔎 评审报告质量",
    }
    return display_names.get(node_name, node_name)


def render_progress_indicator(progress_state):
    """
    渲染进度指示器

    Args:
        progress_state: ProgressState 对象
    """
    st.markdown("### 📊 分析进度")

    # 进度条
    st.progress(progress_state.progress_percent / 100)

    # 当前阶段
    st.info(f"**当前阶段**: {progress_state.current_stage_display}")

    # 三列指标
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("完成进度", f"{progress_state.completed_tasks}/{progress_state.total_tasks} 页")
    with col2:
        remaining = progress_state.get_formatted_remaining_time()
        st.metric("预计剩余", remaining)
    with col3:
        success_rate = progress_state.get_success_rate()
        st.metric("成功率", f"{success_rate:.1f}%")

    # 当前 URL
    if progress_state.current_url:
        st.caption(f"🔗 正在处理: {progress_state.current_url[:80]}...")


def main():
    """主函数"""
    # 显示标题
    st.markdown('<div class="main-header">🎯 面试准备助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">对比官方 JD 与民间面经，发现你的技能 Gap</div>', unsafe_allow_html=True)

    # 检查环境变量
    if not check_env_vars():
        st.stop()

    # 批量初始化 session state（避免多次检查）
    default_state = {
        "analysis_done": False,
        "result": None,
        "resume_content": "",
        "report_saved": False,
        "report_path": "",
        "selected_position": "字节跳动 后端开发 2026校招",
        "analysis_mode": "standard",  # 分析模式：standard 或 quick
        # 新增：后台任务状态跟踪
        "analysis_running": False,      # 是否正在运行
        "analysis_error": None,          # 错误信息
        "analysis_status_msg": "",       # 状态消息
        "analysis_future": None,         # 后台任务 Future 对象
        "results_shown": False,          # 结果是否已显示
        "analysis_run_id": "",           # 任务运行ID（用于自动恢复）
    }

    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # 恢复自动重载导致的状态丢失
    _restore_status_into_session()

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 设置")

        # 分析模式选择
        st.markdown("### 📊 分析模式")
        analysis_mode = st.radio(
            "选择分析模式",
            options=["standard", "quick"],
            format_func=lambda x: "🚀 快速模式 (3-5分钟)" if x == "quick" else "📊 标准模式 (10-15分钟)",
            help="快速模式：简化版报告，10-15页，适合快速了解\n标准模式：完整版报告，30-50页，全面深入",
            key="analysis_mode_radio"
        )

        # 更新 session state
        st.session_state.analysis_mode = analysis_mode

        # 显示模式说明
        if analysis_mode == "quick":
            st.info("**快速模式**：约 10-15 页，3-5 分钟完成，适合快速了解核心差距")
        else:
            st.info("**标准模式**：约 30-50 页，10-15 分钟完成，全面深入分析")

        st.markdown("---")

        # 说明
        st.info("""
        **使用说明：**

        1. 上传你的简历（PDF 或 TXT）
        2. 输入目标岗位
        3. 选择分析模式
        4. 点击"开始分析"
        5. 等待分析完成
        6. 查看详细报告
        """)

        st.markdown("---")

        st.markdown("---")

        # 环境变量状态
        if os.getenv("ZHIPUAI_API_KEY"):
            st.success("✅ ZhipuAI API 已配置")
        else:
            st.error("❌ ZhipuAI API 未配置")

        if os.getenv("TAVILY_API_KEY"):
            st.success("✅ Tavily API 已配置")
        else:
            st.error("❌ Tavily API 未配置")

    # 主界面
    st.header("📝 输入信息")

    # 创建两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📄 上传简历")

        # 文件上传
        uploaded_file = st.file_uploader(
            "选择简历文件",
            type=["pdf", "txt"],
            help="支持 PDF 和 TXT 格式",
            label_visibility="collapsed"
        )

        # 如果有文件上传，读取内容
        if uploaded_file is not None:
            try:
                file_bytes = uploaded_file.read()
                resume_content = extract_text_from_file(uploaded_file.name, file_bytes)
                st.session_state.resume_content = resume_content

                # 显示预览
                with st.expander("📖 简历内容预览", expanded=False):
                    st.text_area(
                        "简历内容",
                        resume_content,
                        height=300,
                        disabled=True,
                        label_visibility="collapsed"
                    )

                st.success(f"✅ 成功读取简历: {uploaded_file.name}")
            except Exception as e:
                st.error(f"❌ 文件读取失败: {str(e)}")

    with col2:
        st.subheader("🎯 目标岗位")

        # 目标岗位输入
        target_position = st.text_input(
            "输入目标公司和岗位",
            value=st.session_state.selected_position,  # 使用 session state 的值
            help="例如: 字节跳动 后端开发 2026校招",
            label_visibility="collapsed",
            key="target_position_input"
        )

        # 常用岗位快捷选择
        st.markdown("**快捷选择:**")
        quick_options = [
            "字节跳动 后端开发 2026校招",
            "腾讯 后端开发 2026校招",
            "阿里巴巴 后端开发 2026校招",
            "美团 后端开发 2026校招",
        ]

        for option in quick_options:
            if st.button(option, key=f"quick_select_{option}", use_container_width=True):
                # 更新 session state 而不是 rerun
                st.session_state.selected_position = option

    # 开始分析按钮
    st.markdown("---")

    if not st.session_state.resume_content:
        st.warning("⚠️ 请先上传简历文件")
    elif not target_position:
        st.warning("⚠️ 请输入目标岗位")
    else:
        # 检查是否已有任务在运行
        if st.session_state.analysis_running:
            st.warning("⚠️ 分析正在进行中，请耐心等待...")
            st.info(f"📊 {st.session_state.analysis_status_msg}")
        elif st.session_state.analysis_error:
            st.error(f"❌ {st.session_state.analysis_error}")
            if st.button("清除错误", key="clear_error"):
                st.session_state.analysis_error = None
                _clear_status_file()
                st.rerun()
        else:
            if st.button("🚀 开始分析", type="primary", use_container_width=True):
                # 调试：记录按钮点击
                import logging
                logger = logging.getLogger(__name__)
                logger.info("="*60)
                logger.info("BUTTON CLICKED: 开始分析")
                logger.info(f"Resume length: {len(st.session_state.resume_content)}")
                logger.info(f"Target position: {target_position}")
                logger.info(f"Analysis mode: {st.session_state.analysis_mode}")
                logger.info("="*60)

                # 限流检查（仅在Hugging Face Spaces环境）
                if os.getenv("SPACE_ID"):
                    # 尝试获取客户端IP
                    try:
                        client_ip = st.context.request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()
                        if not client_ip or client_ip == "unknown":
                            client_ip = "unknown"
                    except Exception:
                        client_ip = "unknown"

                    # 检查限流
                    allowed, error_msg = check_rate_limit(client_ip)
                    if not allowed:
                        st.session_state.analysis_error = error_msg
                        st.error(error_msg)
                        st.info("📊 **使用统计**：")
                        stats = get_usage_stats()
                        st.json(stats)
                        st.stop()

                # 重置状态
                st.session_state.analysis_done = False
                st.session_state.result = None
                st.session_state.analysis_error = None

                # 定义后台任务函数
                # 关键修复：在启动时传递数据，而不是在后台线程中读取 session_state
                resume_data = st.session_state.resume_content
                position_data = target_position
                # 强制使用 quick 模式，加速跑通
                st.session_state.analysis_mode = "quick"
                mode_data = "quick"
                run_id = uuid.uuid4().hex
                st.session_state.analysis_run_id = run_id
                _write_status_file(
                    {
                        "run_id": run_id,
                        "status": "running",
                        "message": "⏳ 任务已启动，正在分析中...",
                        "analysis_mode": mode_data,
                        "started_at": time.time(),
                        "updated_at": time.time(),
                    }
                )

                # 调试：打印分析模式
                import logging
                logging.getLogger(__name__).info(f"🔍 Starting analysis with mode: {mode_data}")

                # 初始化进度追踪器
                tracker = get_progress_tracker()
                tracker.reset()
                tracker.set_analysis_mode(mode_data)
                tracker.update_stage(AnalysisStage.INITIALIZING)

                def run_analysis_background(resume_content, target_position, analysis_mode, run_id):
                    """在后台线程中运行分析

                    注意：这个函数在后台线程中运行，不能访问 st.session_state
                    返回结果字典，由主线程更新 UI 状态
                    """
                    import logging
                    import traceback
                    from pathlib import Path
                    from src.progress_tracker import get_progress_tracker, AnalysisStage

                    logger = logging.getLogger(__name__)
                    logger.info("="*60)
                    logger.info("🚀 BACKGROUND TASK STARTED")
                    logger.info(f"Resume length: {len(resume_content)} chars")
                    logger.info(f"Target position: {target_position}")
                    logger.info(f"Analysis mode: {analysis_mode}")
                    logger.info("="*60)

                    stop_event = threading.Event()
                    _start_progress_heartbeat(run_id, stop_event)

                    try:
                        # 运行分析（传递分析模式）
                        logger.info("📊 Calling run_analysis()...")
                        final_state = run_analysis(resume_content, target_position, analysis_mode)
                        logger.info("✅ run_analysis() completed successfully")
                        logger.info(f"📋 Final state keys: {list(final_state.keys())}")

                        # 更新进度追踪器为完成状态
                        tracker = get_progress_tracker()
                        tracker.update_stage(AnalysisStage.COMPLETE)

                        # 保存报告到文件
                        report_saved = False
                        report_path = ""
                        if final_state.get("final_report"):
                            output_file = Path("interview_preparation_report.md")
                            output_file.write_text(
                                final_state["final_report"],
                                encoding="utf-8"
                            )
                            report_saved = True
                            report_path = str(output_file.absolute())

                        _write_status_file(
                            {
                                "run_id": run_id,
                                "status": "success",
                                "final_report": final_state.get("final_report", ""),
                                "report_path": report_path,
                                "updated_at": time.time(),
                            }
                        )
                        return {
                            "success": True,
                            "final_state": final_state,
                            "report_saved": report_saved,
                            "report_path": report_path
                        }

                    except Exception as e:
                        import traceback
                        import logging

                        # 记录详细错误
                        logger.error("="*60)
                        logger.error("❌ BACKGROUND TASK FAILED")
                        logger.error(f"Error type: {type(e).__name__}")
                        logger.error(f"Error message: {str(e)}")
                        logger.error(f"Full traceback:\n{traceback.format_exc()}")
                        logger.error("="*60)

                        # 更新进度追踪器为错误状态
                        tracker = get_progress_tracker()
                        tracker.update_stage(AnalysisStage.ERROR)
                        
                        _write_status_file(
                            {
                                "run_id": run_id,
                                "status": "error",
                                "error": f"分析失败: {str(e)}",
                                "updated_at": time.time(),
                            }
                        )
                        return {
                            "success": False,
                            "error": f"分析失败: {str(e)}"
                        }
                    finally:
                        stop_event.set()

                # 提交后台任务（不阻塞！）
                logger.info("📤 Submitting background task to executor...")
                executor = get_background_executor()
                future = executor.submit(run_analysis_background, resume_data, position_data, mode_data, run_id)
                logger.info(f"✅ Task submitted. Future object: {future}")
                st.session_state.analysis_future = future
                st.session_state.analysis_running = True
                st.session_state.analysis_status_msg = "⏳ 任务已启动，正在分析中..."

                # 使用status容器显示进度
                st.success("✅ 分析任务已启动！")
                with st.status("📊 分析正在进行中...", expanded=True) as status:
                    st.write("⏳ 后台正在分析您的简历...")
                    st.write("📋 预计需要 3-5 分钟")
                    st.write("⚠️ 请保持此页面打开，分析完成后会自动显示结果")
                    st.write("🔄 页面每 2 秒会自动刷新以显示最新进度")

                logger.info("🔄 About to call st.rerun()...")
                st.rerun()
                logger.info("✅ st.rerun() returned")

    # ========== 优先检查状态文件（兜底机制） ==========
    # 即使 Future 对象失效，也能从状态文件恢复
    status_file = Path(".analysis_status.json")
    if status_file.exists() and st.session_state.analysis_running:
        try:
            import time
            status_data = json.loads(status_file.read_text(encoding="utf-8"))
            status = status_data.get("status")

            # 如果状态文件显示已完成，直接更新 session_state
            if status == "success":
                st.session_state.analysis_running = False
                st.session_state.analysis_done = True
                st.session_state.result = {"final_report": status_data.get("final_report", "")}
                st.session_state.analysis_status_msg = "✅ 分析完成！"
                st.session_state.report_saved = status_data.get("report_path") is not None
                st.session_state.report_path = status_data.get("report_path", "")
                logger.info("✅ Restored success state from status file")
                st.rerun()
            elif status == "error":
                st.session_state.analysis_running = False
                st.session_state.analysis_error = status_data.get("error", "分析失败")
                st.session_state.analysis_status_msg = f"❌ {st.session_state.analysis_error}"
                logger.info("✅ Restored error state from status file")
                st.rerun()
        except Exception as e:
            logger.error(f"Error reading status file: {e}")

    # 检查后台任务是否完成（自动刷新机制）
    if st.session_state.analysis_running and st.session_state.analysis_future:
        future = st.session_state.analysis_future
        try:
            if future.done():
                # 任务已完成，直接获取结果（不会阻塞，因为done()=True）
                try:
                    result = future.result()

                    # 增强日志：确认任务完成和状态
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"✅ Task completed. Success: {result.get('success')}")
                    if result.get('final_state'):
                        logger.info(f"✅ Final state keys: {list(result.get('final_state', {}).keys())}")
                        logger.info(f"✅ Has final_report: {'final_report' in result.get('final_state', {})}")

                    if result["success"]:
                        st.session_state.result = result["final_state"]
                        st.session_state.analysis_done = True
                        st.session_state.analysis_running = False
                        st.session_state.analysis_status_msg = "✅ 分析完成！"

                        if result.get("report_saved"):
                            st.session_state.report_saved = True
                            st.session_state.report_path = result["report_path"]
                    else:
                        st.session_state.analysis_running = False
                        st.session_state.analysis_error = result["error"]
                        st.session_state.analysis_status_msg = f"❌ 分析失败: {result['error']}"

                    # 触发刷新以显示结果
                    logger.info("🔄 Triggering rerun to show results")
                    st.rerun()

                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Error processing result: {e}", exc_info=True)
                    st.session_state.analysis_running = False
                    st.session_state.analysis_error = f"系统错误: {str(e)}"
        except Exception as e:
            logger.error(f"Error checking future: {e}")

    # 显示后台任务状态（保持简洁，不展示流程）
    if st.session_state.analysis_running:
        st.markdown("---")
        st.info("⏳ **分析进行中**，完成后会自动显示报告")
        # 轻量自动刷新
        if "last_refresh_time" not in st.session_state:
            st.session_state.last_refresh_time = time.time()
        if time.time() - st.session_state.last_refresh_time > 2:
            st.session_state.last_refresh_time = time.time()
            st.rerun()

    # 显示结果
    if st.session_state.analysis_done and st.session_state.result:
        st.markdown("---")
        st.header("📊 分析报告")

        final_report = st.session_state.result.get("final_report", "")

        # 调试信息（可展开）
        with st.expander("🔍 调试信息（点击查看）", expanded=False):
            st.write("**最终状态包含的字段:**")
            for key in st.session_state.result.keys():
                value = st.session_state.result[key]
                if isinstance(value, str):
                    st.write(f"- `{key}`: {len(value)} 字符")
                elif isinstance(value, list):
                    st.write(f"- `{key}`: {len(value)} 项")
                else:
                    st.write(f"- `{key}`: {type(value).__name__}")

        if final_report:
            # 使用容器确保报告可见
            report_container = st.container()
            with report_container:
                st.markdown(final_report)

                col1, col2 = st.columns([1, 1])
                with col1:
                    # 下载按钮
                    st.download_button(
                        label="💾 下载报告",
                        data=final_report,
                        file_name="interview_preparation_report.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                with col2:
                    # 开始新分析按钮
                    if st.button("🔄 开始新分析", use_container_width=True):
                        # 重置所有状态
                        st.session_state.analysis_done = False
                        st.session_state.result = None
                        st.session_state.analysis_running = False
                        st.session_state.analysis_error = None
                        st.session_state.analysis_status_msg = ""
                        st.session_state.analysis_run_id = ""
                        _clear_status_file()
                        st.rerun()
        else:
            st.error("❌ 未生成报告内容")
            st.warning(
                "请检查上方的调试信息，"
                "可能数据提取失败导致无法生成报告"
            )
    # 兜底：如果已有本地报告但页面未显示，直接展示
    elif not st.session_state.analysis_running:
        report_file = Path("interview_preparation_report.md")
        if report_file.exists():
            st.markdown("---")
            st.header("📊 分析报告")
            report_text = report_file.read_text(encoding="utf-8")
            st.markdown(report_text)
            st.caption("已从本地报告文件加载")

    # 自动刷新：如果分析已完成但还没显示结果（首次完成时）
    elif st.session_state.analysis_done and not st.session_state.get("results_shown", False):
        st.session_state.results_shown = True
        st.rerun()


if __name__ == "__main__":
    main()
