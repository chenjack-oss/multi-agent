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

## 指标与成果

- **会话隔离**：ContextVar 协程级隔离 + finally 重置，50 会话 × 100 轮并发压测无串台，会话数据 / 中间产物 / 最终报告按会话 ID 完整留存，任意一次调研可回溯复现；
- **效率提升**：单份多数据源商业调研报告从人工数小时缩短到分钟级自动出稿；
- **稳定性**：轮次上限 + Token 阈值双层循环防护拦截 Agent 死循环；会话级任务注册表支持协作式取消，任务结束自动注销防注册表膨胀。

## 压测验证

`benchmark/load_test.py` 提供可复现的多会话并发压测，直接验证上述隔离性声明：

```bash
# 50 并发会话 × 4 轮（真实运行请按 API 配额调整轮次）
python benchmark/load_test.py --sessions 50 --rounds 4 --api http://127.0.0.1:8000 --report loadtest.json
```

验证内容：

| 项 | 方式 |
|---|---|
| 会话隔离（无串台） | 每轮查询注入唯一标记，下载该会话全部产物做归属校验，产物含他人标记即判串台 |
| 轮次收敛与成功率 | 每会话连续 R 轮任务，统计成功率 |
| 延迟分布 | 端到端耗时 p50 / p95 |
| 可回溯性 | 会话产物按 thread_id 目录留存，压测后可逐会话核对 |

结果 JSON 含串台计数（`cross_session_leaks`）与失败明细，可直接作为稳定性验收依据。

## 依赖服务

- RAGFlow（知识库服务，需自行部署）
- MySQL 8.x（业务数据库）
- 阿里云百炼 DashScope（LLM 服务）
- Tavily API（网络搜索服务）

## License

MIT
