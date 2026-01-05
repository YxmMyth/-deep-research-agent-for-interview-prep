# Market-Reality Aligned Interview Agent

基于市场实情的求职辅助智能体，通过对比 **官方 JD** 与 **民间面经**，帮助用户发现简历与市场需求的 Gap，生成有数据支撑的备战报告。

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

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 Poetry (如果尚未安装)
pip install poetry

# 安装项目依赖
poetry install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入 API Keys:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

### 3. 运行 Agent

```bash
poetry run python main.py
```

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
