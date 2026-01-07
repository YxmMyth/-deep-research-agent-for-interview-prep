# Market-Reality Aligned Interview Agent

基于市场实情的求职辅助智能体，通过对比 **官方 JD** 与 **民间面经**，帮助用户发现简历与市场需求的 Gap，生成有数据支撑的备战报告。

## 🌐 在线使用（推荐）

[![Hugging Face Spaces](https://img.shields.io/badge/🤗-Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/Evannnnn/interview-prep-agent)

**[点击这里立即使用 →](https://huggingface.co/spaces/Evannnnn/interview-prep-agent)**

✅ 无需安装，无需配置API Key
✅ 直接上传简历即可使用
✅ 完全免费服务

---

## 🎯 核心特性

- **ETL Pipeline**: Crawl4AI → Clean Markdown → ScrapeGraphAI → Pydantic Object
- **并行搜索**: JD 和面经搜索并行执行，提高效率
- **三重对比分析**:
  1. 简历 vs JD
  2. JD vs 面经
  3. 简历 vs 面经
- **Reflexion 循环**: Writer → Critic → Writer (最多 3 次迭代优化报告)

## 📦 技术栈

| 层级 | 技术选型 |
|------|----------|
| Orchestration | LangGraph (StateGraph) >= 0.2.0 |
| LLM | OpenAI GPT-4o |
| Search | Tavily API |
| Web Cleaning | Crawl4AI >= 0.3.0 |
| Structured Extraction | ScrapeGraphAI >= 1.0.0 |
| Schema Validation | Pydantic V2 >= 2.0 |

## 🚀 使用方式

### 方式一：在线服务（推荐）

访问 [Hugging Face Spaces](https://huggingface.co/spaces/Evannnnn/interview-prep-agent) 直接使用，无需任何配置。

**使用限制**（为了防止滥用）：
- 每个IP每天最多5次分析
- 全局每天最多100次分析
- 超限后可本地部署使用

### 方式二：本地部署

如果你需要更频繁的使用或想自建服务，可以本地部署：

#### 1. 安装依赖

```bash
# 使用 Poetry 安装 (推荐)
pip install poetry
poetry install

# 或使用 pip 直接安装
pip install langgraph langchain langchain-openai langchain-community openai pydantic python-dotenv crawl4ai scrapegraphai tavily-python rich streamlit pymupdf
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入 API Keys:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
ZHIPUAI_API_KEY=你的完整Key
TAVILY_API_KEY=tvly-...
```

### 3. 运行 Agent

#### 网页版 (推荐)

```bash
streamlit run web_app.py
```

网页版特性:
- 📄 支持 PDF/TXT 简历上传
- 🎯 可视化目标岗位输入
- 🔄 实时显示分析进度
- 📊 网页内直接查看报告
- 💾 一键下载 Markdown 报告

#### 命令行版

```bash
python main.py
```

按照提示输入简历内容（以 END 结束）和目标岗位。

## 📁 项目结构

```
market_interview_agent/
├── pyproject.toml          # Poetry 依赖管理
├── .env.example            # 环境变量模板
├── main.py                 # CLI 入口
├── src/
│   ├── schemas.py          # Pydantic 数据模型
│   ├── state.py            # LangGraph AgentState 定义
│   ├── graph.py            # LangGraph 工作流定义
│   ├── nodes/              # 各节点实现
│   │   ├── planner.py      # Node 1: 生成研究计划
│   │   ├── researcher.py   # Node 2: 并行搜索与抓取
│   │   ├── analyst.py      # Node 3: Gap 分析
│   │   └── writer.py       # Node 4: 报告生成 + Reflexion
│   ├── tools/
│   │   ├── scraper.py      # ETL Pipeline: Crawl4AI + ScrapeGraphAI
│   │   └── search.py       # Tavily 搜索封装
│   └── prompts/
│       └── templates.py    # Prompt 模板集中管理
└── tests/
    └── test_scraper.py     # 单元测试
```

## 🧪 运行测试

```bash
poetry run pytest tests/test_scraper.py -v -s
```

## 📊 工作流程

```
┌──────────┐      ┌──────────────┐
│  Planner │ ────> │ Researchers  │
└──────────┘      │  (并行)       │
                  └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Gap Analyst  │
                  └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Writer      │◄──┐
                  └──────────────┘   │
                         │           │
                         ▼           │
                  ┌──────────────┐   │
                  │   Critic     │───┘
                  └──────────────┘
```

## 📝 License

MIT License

## 🙏 致谢

- **托管**: 感谢 [Hugging Face Spaces](https://huggingface.co/spaces) 提供免费托管服务
- **LLM**: 使用 [智谱AI GLM-4](https://open.bigmodel.cn/) 提供分析能力
- **搜索**: 使用 [Tavily](https://tavily.com/) 提供搜索API
- **框架**: 基于 [LangGraph](https://github.com/langchain-ai/langgraph) 构建

## 📮 反馈与建议

如有问题或建议，欢迎：
- 提交 [Issue](https://github.com/你的用户名/DeepResearchAgentV2/issues)
- 发起 [Pull Request](https://github.com/你的用户名/DeepResearchAgentV2/pulls)

## ⭐ Star History

如果这个项目对你有帮助，请给它一个星标！
