# 面试准备助手 - 开发文档

## 项目概述

这是一个基于 LangGraph 的智能面试准备助手，通过对比简历、官方 JD 和真实面试经验，帮助求职者发现技能差距并提供改进建议。

**核心功能**：
- 三维度分析：简历 vs JD、JD vs 面试经验、简历 vs 面试经验
- 自动搜索：并行搜索职位描述和面试经验
- 智能报告：生成包含学习资源和时间表的备战报告
- 两种入口：CLI 命令行版和 Streamlit 网页版

## 技术栈

### 核心框架
- **LangGraph >= 0.2.0**: 工作流编排
- **LangChain >= 0.3.0**: LLM 抽象层
- **Pydantic >= 2.0**: 数据验证和结构化提取

### LLM 和 API
- **ZhipuAI GLM-4**: 主要 LLM（中文优化）
- **Tavily API**: 网络搜索
- **Crawl4AI >= 0.3.0**: 网页抓取和清理
- **ScrapeGraphAI >= 1.0.0**: 结构化数据提取

### 网页界面
- **Streamlit >= 1.28.0**: Web UI
- **nest-asyncio**: Async 兼容性（已移除，改用线程池方案）

### 其他依赖
- **PyMuPDF >= 1.23.0**: PDF 解析
- **python-dotenv**: 环境变量管理
- **rich**: CLI 美化输出

## 项目结构

```
DeepResearchAgentV2/
├── src/
│   ├── graph.py              # LangGraph 工作流定义
│   ├── state.py              # 全局状态定义（TypedDict）
│   ├── schemas.py            # Pydantic 数据模型
│   ├── llm.py                # LLM 调用层（ZhipuAI）
│   ├── prompts/              # 提示词模板
│   ├── nodes/                # 工作流节点
│   │   ├── planner.py        # 生成搜索计划
│   │   ├── researcher.py     # JD 和面试经验搜索（并行）
│   │   ├── analyst.py        # 差距分析
│   │   ├── writer.py         # 报告生成
│   │   └── critic.py         # 报告评审（Reflexion 循环）
│   ├── tools/                # 工具函数
│   │   ├── scraper.py        # ETL 管道（Crawl4AI → 清理 → LLM）
│   │   └── search.py         # Tavily API 包装
│   └── utils/                # 工具类
│       └── pdf_parser.py     # PDF/TXT 解析
├── main.py                   # CLI 入口点
├── web_app.py                # Streamlit Web 入口点
├── run_web.bat               # Windows 启动脚本
└── pyproject.toml            # 项目依赖

```

## 工作流架构

```
┌─────────────┐
│   Planner   │ 生成搜索查询
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
┌──────▼──────┐   ┌─────▼──────┐
│ JD Research │   │ Interview  │ 并行搜索
│             │   │ Research   │
└──────┬──────┘   └─────┬──────┘
       │                 │
       └────────┬────────┘
                │
       ┌────────▼────────┐
       │  Gap Analyst    │ 三维度差距分析
       └────────┬────────┘
                │
       ┌────────▼────────┐
       │  Report Writer  │ 生成报告
       └────────┬────────┘
                │
       ┌────────▼────────┐
       │     Critic      │ 评审（最多 3 次迭代）
       └────────┬────────┘
                │
          (如果不通过)
                │
       ┌────────▼────────┐
       │  Report Writer  │ 重新生成
       └─────────────────┘
```

## 环境配置

### 必需的环境变量

创建 `.env` 文件：

```bash
# ZhipuAI API 密钥（用于 LLM 调用）
ZHIPUAI_API_KEY=你的完整密钥

# Tavily API 密钥（用于网络搜索）
TAVILY_API_KEY=tvly-你的密钥
```

### Python 版本

- **推荐**: Python 3.10 - 3.13
- **注意**: Python 3.14+ 有兼容性问题（见下方已知问题）

## 安装和运行

### 使用 Poetry（推荐）

```bash
# 安装依赖
poetry install

# CLI 版本
poetry run python main.py

# Web 版本
poetry run streamlit run web_app.py
```

### 使用 pip

```bash
# 安装依赖
pip install -r requirements.txt  # 或手动从 pyproject.toml 安装

# CLI 版本
python main.py

# Web 版本
streamlit run web_app.py
```

### Windows 快速启动

双击 `run_web.bat` 启动 Web 版本

## 关键修复记录

### 问题 1: Streamlit + LangGraph Async 冲突（已解决 ✅）

**症状**：
- Web 版点击"开始分析"后卡住不动
- 错误：`RuntimeError: Timeout should be used inside a task`

**根本原因**：
- Python 3.14 的新 `asyncio.timeout()` API 与 `nest_asyncio` 不兼容
- LangGraph 内部使用了 `asyncio.timeout()`
- Streamlit 的 event loop 与 LangGraph 的 async 执行冲突

**解决方案**：
- 使用 `ThreadPoolExecutor` 在独立线程中运行异步代码
- 每个线程有自己独立的 event loop，避免嵌套问题
- 位置：`web_app.py` 的 `run_analysis()` 函数

**关键代码**（web_app.py:104-140）：
```python
def run_analysis(resume_content: str, target_position: str) -> dict:
    async def analysis_async():
        # ... 异步代码

    # 在单独的线程中运行，避免 Streamlit event loop 冲突
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(lambda: asyncio.run(analysis_async()))
        return future.result()
```

### 问题 2: 报告显示问题（已解决 ✅）

**症状**：
- 报告生成后显示在最底部，用户看不到

**解决方案**：
- 添加 `st.toast()` 通知提示用户向下滚动
- 使用 `st.container()` 确保报告正确渲染
- 改进进度提示，显示 "⚙️ 初始化工作流..."、"💾 正在保存报告..."

### 问题 3: Windows GBK 编码问题（待修复 ⚠️）

**症状**：
- 错误：`'gbk' codec can't encode character '\u2713' in position 0: illegal multibyte sequence`
- 影响：部分网页抓取失败

**临时方案**：
- 已设置 `PYTHONIOENCODING=utf-8`
- 大部分功能正常工作，部分抓取可能失败

**长期方案**：
- 需要修复爬虫中的编码处理（src/tools/scraper.py）

## 使用说明

### Web 版本

1. 访问 http://localhost:8501
2. 上传简历（PDF 或 TXT）
3. 输入目标岗位（或使用快捷选择）
4. 点击"开始分析"
5. 等待完成，查看报告

### CLI 版本

```bash
python main.py
```

按提示：
1. 粘贴简历内容（以 `END` 结束）
2. 输入目标岗位
3. 等待分析完成
4. 报告保存到 `interview_preparation_report.md`

## 已知问题

1. **Python 3.14 兼容性**
   - `asyncio.WindowsProactorEventLoopPolicy` 已弃用，将在 Python 3.16 移除
   - 建议：使用 Python 3.10-3.13

2. **Windows GBK 编码**
   - 部分网页抓取可能失败
   - 影响范围：部分 JD 和面试经验提取失败
   - 不影响核心功能

3. **LangChain Pydantic V1 兼容性**
   - 警告：`Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater`
   - 影响：仅警告，不影响功能

## 开发注意事项

### 修改 Web 版本时

- **不要** 在 Streamlit 回调中直接使用 `asyncio.run()`
- **使用** `ThreadPoolExecutor` 包装异步代码
- **参考** `web_app.py` 的 `run_analysis()` 函数

### 修改爬虫时

- 确保正确处理 UTF-8 编码
- 考虑 Windows GBK 编码问题
- 在爬虫中显式指定 `encoding='utf-8'`

### 修改工作流时

- 使用 `src/graph.py` 的 `build_graph()` 函数
- 节点必须是异步函数（`async def`）
- 状态更新使用 TypedDict 结构

## 测试

### Web 版测试清单

- [ ] 上传简历成功
- [ ] 输入岗位成功
- [ ] 点击分析不卡住
- [ ] 显示进度更新
- [ ] 分析完成有 toast 通知
- [ ] 报告正确显示
- [ ] 下载按钮工作

### CLI 版测试清单

- [ ] 粘贴简历成功
- [ ] 输入岗位成功
- [ ] 分析正常执行
- [ ] 报告保存到文件

## 贡献指南

提交 PR 前请确保：
1. 所有测试通过
2. 代码符合 Black 和 isort 格式
3. 添加必要的注释和文档
4. 测试 Web 和 CLI 两个版本

## 许可证

MIT License

## 联系方式

GitHub: https://github.com/YxmMyth/-deep-research-agent-for-interview-prep
