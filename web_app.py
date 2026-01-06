"""
Market-Reality Aligned Interview Agent - Streamlit Web App

网页版面试准备助手
"""

import asyncio
import os
import sys
import concurrent.futures
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv

# Windows 编码和 asyncio 修复
if sys.platform == "win32":
    # 强制使用 UTF-8 编码
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        # 如果 WindowsProactorEventLoopPolicy 不可用，使用默认策略
        pass

import streamlit as st
from streamlit import status

from src.graph import build_graph
from src.utils.pdf_parser import extract_text_from_file

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


def check_env_vars():
    """检查必需的环境变量"""
    required_vars = ["ZHIPUAI_API_KEY", "TAVILY_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        st.error(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
        st.info("请在项目根目录创建 .env 文件并设置以下变量：")
        st.code("""
ZHIPUAI_API_KEY=你的完整Key
TAVILY_API_KEY=tvly-...
        """)
        return False

    return True


def run_analysis(resume_content: str, target_position: str) -> dict:
    """
    运行分析流程（使用线程池避免 asyncio 嵌套问题）

    Args:
        resume_content: 简历内容
        target_position: 目标岗位

    Returns:
        分析最终状态 (final_state)
    """
    async def analysis_async():
        try:
            graph = build_graph()

            initial_state = {
                "resume_content": resume_content,
                "target_position": target_position,
                "job_descriptions": [],
                "interview_logs": [],
                "revision_count": 0,
            }

            # 使用 ainvoke 运行工作流
            final_state = await graph.ainvoke(initial_state)
            return final_state

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Analysis failed: {e}", exc_info=True)
            raise

    # 在单独的线程中运行异步代码，避免 Streamlit event loop 冲突
    # 这解决了 asyncio.timeout() 与 nest_asyncio 的兼容性问题
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(lambda: asyncio.run(analysis_async()))
        return future.result()


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


def main():
    """主函数"""
    # 显示标题
    st.markdown('<div class="main-header">🎯 面试准备助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">对比官方 JD 与民间面经，发现你的技能 Gap</div>', unsafe_allow_html=True)

    # 检查环境变量
    if not check_env_vars():
        st.stop()

    # 初始化 session state
    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False
    if "result" not in st.session_state:
        st.session_state.result = None
    if "resume_content" not in st.session_state:
        st.session_state.resume_content = ""
    if "report_saved" not in st.session_state:
        st.session_state.report_saved = False
    if "report_path" not in st.session_state:
        st.session_state.report_path = ""

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 设置")

        # 说明
        st.info("""
        **使用说明：**

        1. 上传你的简历（PDF 或 TXT）
        2. 输入目标岗位
        3. 点击"开始分析"
        4. 等待分析完成
        5. 查看详细报告
        """)

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
            value="字节跳动 后端开发 2026校招",
            help="例如: 字节跳动 后端开发 2026校招",
            label_visibility="collapsed"
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
            if st.button(option, key=option, use_container_width=True):
                target_position = option
                st.rerun()

    # 开始分析按钮
    st.markdown("---")

    if not st.session_state.resume_content:
        st.warning("⚠️ 请先上传简历文件")
    elif not target_position:
        st.warning("⚠️ 请输入目标岗位")
    else:
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            st.session_state.analysis_done = False
            st.session_state.result = None

            # 显示进度
            with st.status("🔄 正在分析中，请稍候...", expanded=True) as status:
                try:
                    status.write("⚙️ 初始化工作流...")

                    # 运行分析
                    final_state = run_analysis(
                        st.session_state.resume_content,
                        target_position
                    )

                    # 保存到 session state
                    st.session_state.result = final_state
                    st.session_state.analysis_done = True

                    # 保存报告到文件
                    if final_state.get("final_report"):
                        status.write("💾 正在保存报告...")
                        output_file = Path("interview_preparation_report.md")
                        output_file.write_text(
                            final_state["final_report"],
                            encoding="utf-8"
                        )
                        st.session_state.report_saved = True
                        st.session_state.report_path = str(output_file.absolute())

                    # 标记完成
                    status.update(
                        label="✅ 分析完成！",
                        state="complete",
                        expanded=False
                    )

                    # 显示成功消息
                    if final_state.get("final_report"):
                        st.success("✅ 报告生成成功！")
                        st.toast("✅ 分析完成！请向下滚动查看报告", icon="🎉")
                        if st.session_state.get("report_saved"):
                            st.info(
                                f"📄 报告已保存至: `{st.session_state.report_path}`"
                            )

                except Exception as e:
                    # 增强错误处理
                    status.update(
                        label=f"❌ 分析失败",
                        state="error",
                        expanded=True
                    )
                    st.error(f"**错误详情**: {str(e)}")
                    st.exception(e)

                    st.warning("""
                    **可能的原因:**
                    1. API 密钥配置错误
                    2. 网络连接问题
                    3. 简历内容格式异常

                    **建议操作:**
                    - 检查侧边栏的 API 配置状态
                    - 尝试重新上传简历
                    - 查看上方详细错误信息
                    """)

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

                # 下载按钮
                st.download_button(
                    label="💾 下载报告",
                    data=final_report,
                    file_name="interview_preparation_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
        else:
            st.error("❌ 未生成报告内容")
            st.warning(
                "请检查上方的调试信息，"
                "可能数据提取失败导致无法生成报告"
            )


if __name__ == "__main__":
    main()
