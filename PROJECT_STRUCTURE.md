# 项目文件结构

```
DeepResearchAgent JobInterviewPrep/
│
├── src/                          # 源代码目录
│   ├── __init__.py              # 包初始化
│   ├── state.py                 # Agent 状态定义 (核心)
│   ├── config.py                # 配置管理
│   ├── graph.py                 # LangGraph 工作流定义 (核心)
│   │
│   ├── nodes/                   # 节点实现
│   │   ├── __init__.py
│   │   ├── router.py            # 路由节点：决定下一步行动
│   │   ├── tools.py             # 工具执行节点：调用 API
│   │   ├── analyst.py           # 分析节点：LLM 汇总分析
│   │   └── reporter.py          # 报告节点：生成 Markdown
│   │
│   ├── tools/                   # 工具实现
│   │   ├── __init__.py
│   │   ├── github_tool.py       # GitHub API 自定义工具 ⭐
│   │   └── tavily_tool.py       # Tavily 搜索工具封装
│   │
│   └── utils/                   # 工具类
│       ├── __init__.py
│       ├── llm.py               # LLM 初始化
│       └── charts.py            # ECharts HTML 生成
│
├── tests/                       # 测试目录
│   ├── __init__.py
│   └── test_tools.py            # 工具测试
│
├── main.py                      # 主入口文件
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── README.md                    # 项目文档
└── PROJECT_STRUCTURE.md         # 本文件

```

## 核心文件说明

### 1. `src/state.py`
**作用**: 定义整个工作流的状态结构

**关键类型**:
- `AgentState`: 主状态类，包含所有节点需要共享的数据
- `GitHubStats`: GitHub 统计数据结构
- `NewsArticle`: 新闻文章结构
- `InterviewExperience`: 面试经验结构

**设计要点**:
- 使用 `TypedDict` 保证类型安全
- 使用 `operator.add` 实现 errors 字段的累加
- 所有字段都有明确的 Optional 标注

### 2. `src/graph.py`
**作用**: 构建 LangGraph 工作流

**关键函数**:
- `create_research_graph()`: 创建工作流图
- `run_research_agent()`: 运行 Agent 的主入口
- `get_markdown_report()`: 便捷函数，直接获取报告

**工作流图结构**:
```
Router → Tools → Router → Analyst → Reporter → END
         ↑____________________________|
```

### 3. `src/tools/github_tool.py`
**作用**: 自定义工具，调用 GitHub API

**核心方法**:
- `_search_organization()`: 搜索组织
- `_get_organization_repos()`: 获取仓库列表
- `_calculate_language_distribution()`: 计算语言分布
- `_generate_echarts_config()`: 生成 ECharts 配置

**错误处理**:
- API 限流 → 自动重试 3 次
- 组织不存在 → 返回默认值
- 网络超时 → 超时控制

### 4. `src/nodes/router.py`
**作用**: 路由节点，决定数据收集策略

**逻辑**:
1. 检查已收集的数据
2. 更新 need_* 标志位
3. 决定下一步是 tools 还是 analyst

### 5. `src/nodes/tools.py`
**作用**: 执行工具调用

**调用工具**:
- `GitHubStatsTool`: 获取技术栈
- `TavilySearchTool`: 搜索新闻和面经

### 6. `src/nodes/analyst.py`
**作用**: 汇总分析数据

**功能**:
- 使用 LLM 生成深度分析
- 提取关键洞察

### 7. `src/nodes/reporter.py`
**作用**: 生成最终报告

**输出**:
- 结构化的 Markdown 报告
- 包含 ECharts JSON 配置

## 数据流

```
用户输入公司名
    ↓
Router 分析需求
    ↓
Tools 调用 API (GitHub, Tavily)
    ↓
Router 再次检查
    ↓
Analyst LLM 分析
    ↓
Reporter 生成报告
    ↓
输出 Markdown + ECharts
```

## 扩展点

### 添加新工具
1. 在 `src/tools/` 创建新文件
2. 实现工具类
3. 在 `src/nodes/tools.py` 中调用

### 添加新节点
1. 在 `src/nodes/` 创建新文件
2. 实现节点函数
3. 在 `src/graph.py` 中添加到工作流

### 自定义报告
修改 `src/nodes/reporter.py` 中的 `_generate_markdown_report()` 函数
