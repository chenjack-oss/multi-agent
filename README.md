# Multi-Agent

基于 LangGraph 构建的多智能体深度搜索系统，通过主智能体编排「数据库查询（NL2SQL）+ 知识库检索（RAG）+ 网络搜索」三个子智能体，实现对复杂问题的多源信息融合与深度推理。

## 项目特性

- **多智能体编排**：主智能体（Supervisor）根据问题意图动态路由到子智能体，支持串行/并行调度与结果汇总
- **三类子智能体**：
  - `database_query_agent`：自然语言转 SQL，查询结构化数据库
  - `knowledge_base_agent`：对接 RAGFlow，检索非结构化知识库
  - `network_search_agent`：基于 Tavily 的实时网络搜索
- **FastAPI 服务化**：内置 API 服务与调用监控
- **可配置提示词**：提示词与代码分离，通过 `prompt/prompts.yml` 集中管理

## 技术栈

| 类别 | 选型 |
|------|------|
| 编排框架 | LangGraph |
| Web 框架 | FastAPI + Uvicorn |
| LLM | Qwen 系列（阿里云百炼 DashScope，OpenAI 兼容接口） |
| 知识库 | RAGFlow |
| 网络搜索 | Tavily API |
| 数据库 | MySQL |
| 配置管理 | YAML |

## 目录结构

```
.
├── agent/
│   ├── main_agent.py              # 主智能体（Supervisor 编排）
│   ├── llm.py                     # LLM 调用封装
│   ├── prompts.py                 # 提示词
│   └── subagents/                 # 子智能体
│       ├── database_query_agent.py    # NL2SQL 数据库查询
│       ├── knowledge_base_agent.py    # RAGFlow 知识库检索
│       └── network_search_agent.py    # Tavily 网络搜索
├── api/
│   ├── server.py                  # FastAPI 服务入口
│   ├── context.py                 # 请求上下文
│   └── monitor.py                 # 调用监控
├── rawflow/                       # RAG 基础流程 demo
│   ├── rag_config.py
│   ├── knowledge_demo.py
│   └── chat_assistant_demo.py
├── tools/                         # 工具集
│   ├── db_tools.py                # 数据库工具
│   ├── ragflow_tools.py           # RAGFlow 工具
│   ├── tavily_tool.py             # Tavily 搜索工具
│   ├── markdown_tools.py          # Markdown 处理
│   ├── pdf_tools.py               # PDF 处理
│   └── upload_file_read_tool.py   # 上传文件读取
├── utils/
│   ├── path_utils.py              # 路径工具
│   └── word_converter.py          # Word 转换
├── prompt/
│   └── prompts.yml                # 提示词配置
├── pyproject.toml
├── requirements.txt
└── .env.example                   # 环境变量模板
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或使用 [uv](https://github.com/astral-sh/uv)：

```bash
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

按需修改 `.env` 中的以下配置：

- **LLM**：`OPENAI_API_KEY`、`OPENAI_BASE_URL`（阿里云百炼 DashScope）
- **RAGFlow**：`RAGFLOW_API_URL`、`RAGFLOW_API_KEY`
- **网络搜索**：`TAVILY_API_KEY`
- **数据库**：`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`、`MYSQL_HOST`、`MYSQL_PORT`

### 3. 启动服务

```bash
python -m api.server
```

或直接：

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问 `http://localhost:8000/docs` 查看 API 文档。

## 依赖服务

- RAGFlow（知识库服务，需自行部署）
- MySQL 8.x（业务数据库）
- 阿里云百炼 DashScope（LLM 服务）
- Tavily API（网络搜索服务）

## License

MIT
