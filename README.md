# 医疗 Agent RAG 系统

![系统架构图](./images/img.png)
![系统界面](./images/img_1.png)

一个基于 `FastAPI + Streamlit + LangChain + LangGraph + Ollama + PostgreSQL/pgvector` 的本地医疗知识问答项目。它同时提供两条主链路：

- `Agent` 模式：先检索知识库，再由 Tool Calling Agent 按需调用医疗工具与检索工具完成回答
- `RAG` 模式：直接走混合检索 + 上下文生成，适合更稳定的知识库直答

当前代码已经具备知识库导入、混合检索、流式问答、会话记忆、文件上传、增量更新和前端管理页面等完整闭环。

## 项目亮点

- 双问答模式
  - `/query`、`/query-stream` 走 Agent
  - `/query-rag`、`/query-stream-rag` 走纯 RAG
- 混合检索链路
  - PGVector 语义召回
  - 轻量 BM25 关键词召回
  - 线性融合重排
  - 低置信命中提示
- 分层记忆
  - 短期记忆：最近几轮原始对话
  - 事实记忆：年龄、性别、病史、药物、过敏、持续症状
  - 摘要记忆：长会话阶段摘要
- 知识库管理
  - 支持 `PDF / DOCX / TXT`
  - MD5 去重
  - 单文件上传、批量上传
  - 增量更新、全量更新
  - 文件状态查看：`pending / vectorized`
- 前端可直接操作
  - 聊天页
  - 知识库页
  - 设置页
  - 流式输出
  - 工具调用展示
  - 来源片段展示

## 实际技术栈

| 层 | 实现 |
| --- | --- |
| API | FastAPI |
| 前端 | Streamlit |
| Agent | LangChain `create_agent` + LangGraph checkpoint |
| LLM | Ollama `qwen2.5:7b` |
| Embedding | Ollama `bag-m3:latest` |
| 向量库 | PostgreSQL + pgvector + `langchain-postgres` |
| 文档处理 | `pypdf`、`docx2txt`、`langchain-community` |
| 日志 | Loguru |

说明：

- 代码和 `.env.example` 当前默认嵌入模型写的是 `bag-m3:latest`
- 如果你本地实际安装的是别的 Ollama embedding 模型，请把 `.env` 里的 `EMBEDDING_MODEL` 改成你的真实模型名

## 系统架构

### 1. 问答链路

`Agent` 模式：

1. 读取 PostgreSQL 中的短期记忆、事实记忆、摘要记忆
2. 执行混合检索，提前拿到候选文档
3. 将记忆和检索上下文一起注入 Agent
4. Agent 按需调用工具
5. 保存问答记录，并抽取事实记忆、阶段摘要

`RAG` 模式：

1. 执行混合检索
2. 命中知识库时走 `generate_with_context`
3. 没命中时回退到聊天模式
4. 保存会话历史

### 2. 检索链路

项目当前不是“只有向量检索”，而是这套组合：

1. `MedicalVectorStore.similarity_search_with_score`
2. `LightweightBM25Retriever` 对已入库文本块做关键词召回
3. `LightweightReranker` 融合向量分数、关键词分数、词项重叠
4. 对低置信命中返回显式提示

### 3. 数据存储

PostgreSQL 中主要会看到这些数据：

- `langchain_pg_collection` / `langchain_pg_embedding`
  - LangChain PGVector 使用的向量表
- `conversation_history`
  - 问答历史
- `patient_fact_memory`
  - 事实记忆
- `conversation_summary`
  - 阶段摘要

## 目录结构

```text
Medical_rag/
├── agents/                 # Tool Calling Agent
├── api/                    # FastAPI 路由与 Schema
├── app/                    # Streamlit 模块化前端
├── data/
│   ├── medical_docs/       # 知识库原始文档
│   └── md5_records.txt     # 已导入文件的 MD5 记录
├── database/               # SQLAlchemy 连接与模型
├── images/                 # README 截图
├── llm/                    # Ollama 客户端封装
├── logs/                   # 运行日志
├── memory/                 # 分层记忆
├── rag/                    # 检索、切分、向量化、更新
├── tests/                  # 脚本式测试与定向测试
├── tools/                  # Agent 工具
├── app_streamlit.py        # Streamlit 入口
├── config.py               # 后端配置
├── main.py                 # FastAPI 入口
├── QUICKSTART.md           # 旧版快速说明
├── PROJECT_ANALYSIS_AND_OPTIMIZATION.md
├── requirements.txt
└── setup.py
```

## 核心模块说明

### 后端入口

- `main.py`
  - 创建 FastAPI 应用
  - 初始化数据库
  - 注册 `/api/v1` 路由

### Agent

- `agents/medical_agent.py`
  - 创建 Tool Calling Agent
  - 预检索知识库
  - 注入分层记忆
  - 保存 Agent 交互

当前 Agent 默认加载 6 个工具：

- `analyze_symptoms`
- `calculate_bmi`
- `classify_blood_pressure`
- `recommend_department`
- `search_medical_knowledge`
- `get_disease_info`

### RAG

- `rag/rag_chain.py`
  - 文档导入
  - 标准问答
  - 流式问答
  - 统计信息
- `rag/retriever.py`
  - 混合检索诊断信息
- `rag/bm25_retriever.py`
  - 中文/英文兼容的轻量关键词检索
- `rag/reranker.py`
  - 轻量融合重排

### 记忆

- `memory/conversation_memory.py`
  - 短期记忆
  - 事实记忆
  - 摘要记忆
  - 会话统计与会话清理

### 前端

- `app_streamlit.py`
  - 页面路由与整体装配
- `app/pages/chat_page.py`
  - 聊天页
- `app/pages/knowledge_page.py`
  - 知识库页
- `app/pages/settings_page.py`
  - 设置页

## 环境要求

建议环境：

- Python `3.11+`
- PostgreSQL `15+` 或兼容版本
- `pgvector` 扩展
- Ollama

推荐先准备好两个模型：

```bash
ollama pull qwen2.5:7b
ollama pull bag-m3:latest
```

如果 `bag-m3:latest` 在你的 Ollama 环境中不可用，可以换成你本地已安装的 embedding 模型，并同步修改 `.env`。

## 安装与启动

### 1. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

如果你要使用文件上传接口，再额外安装一次：

```bash
pip install python-multipart
```

说明：当前 `requirements.txt` 里没有显式包含 `python-multipart`，但 FastAPI 的上传接口实际需要它。

### 2. 配置 PostgreSQL + pgvector

示例：

```sql
CREATE DATABASE medical_rag;
\c medical_rag
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. 配置 `.env`

```bash
copy .env.example .env
```

请重点修改这些值：

```env
DATABASE_URL=postgresql://username:password@localhost:5432/medical_rag
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=bag-m3:latest
LLM_MODEL=qwen2.5:7b
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
LOG_LEVEL=INFO
```

注意：

- `.env.example` 当前数据库地址是一个局域网 IP 示例，不适合直接拿来运行
- 必须改成你自己的数据库连接串

### 4. 可选：执行初始化脚本

```bash
python setup.py
```

这个脚本会：

- 检查 Python 版本
- 创建 `logs/` 和 `data/medical_docs/`
- 可选安装依赖
- 可选复制 `.env`

### 5. 启动后端

```bash
python main.py
```

启动后可访问：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`

### 6. 启动前端

```bash
python -m streamlit run app_streamlit.py
```

前端地址：

- `http://localhost:8501`

## 第一次使用建议

### 方式一：直接把文档放到目录里

将文档放入：

```text
data/medical_docs/
data/medical_docs/general/
data/medical_docs/cardiology/
data/medical_docs/endocrinology/
```

然后执行增量更新：

```bash
curl -X POST "http://localhost:8000/api/v1/update/incremental"
```

### 方式二：通过前端上传

1. 打开知识库页面
2. 选择分类
3. 上传 `pdf/docx/txt`
4. 前端会先调用 `/upload`
5. 再调用 `/ingest-file` 完成入库

## 文档与分类规则

- 支持格式：`pdf`、`docx`、`txt`
- 单文件上传最大值：`50MB`
- MD5 去重基于文件内容哈希
- 分类既可以显式传入，也可以从目录推断
- 当文档位于 `data/medical_docs/<category>/xxx.txt` 时，系统会优先把 `<category>` 识别为分类

## API 概览

### 问答接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/query` | Agent 标准问答 |
| `POST` | `/api/v1/query-stream` | Agent 流式问答 |
| `POST` | `/api/v1/query-rag` | 纯 RAG 标准问答 |
| `POST` | `/api/v1/query-stream-rag` | 纯 RAG 流式问答 |
| `GET` | `/api/v1/health` | 健康检查 |

### 知识库接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/ingest` | 导入目录 |
| `POST` | `/api/v1/ingest-file` | 导入单个文件 |
| `POST` | `/api/v1/update/incremental` | 增量更新 |
| `POST` | `/api/v1/update/full` | 全量更新 |
| `GET` | `/api/v1/stats` | 获取统计信息 |
| `POST` | `/api/v1/documents/delete` | 删除向量文档块 |

### 文件管理接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/upload` | 单文件上传 |
| `POST` | `/api/v1/upload/batch` | 批量上传 |
| `GET` | `/api/v1/files` | 文件列表 |
| `DELETE` | `/api/v1/files/{filename}` | 删除文件 |

## 问答请求示例

### Agent 问答

```bash
curl -X POST "http://localhost:8000/api/v1/query" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"我身高175cm，体重70kg，BMI是多少？\",\"session_id\":\"demo-session\",\"k\":3,\"category\":\"general\"}"
```

### 纯 RAG 问答

```bash
curl -X POST "http://localhost:8000/api/v1/query-rag" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"感冒一般如何处理？\",\"session_id\":\"demo-rag\",\"k\":5,\"category\":\"general\"}"
```

### 响应结构

```json
{
  "question": "感冒一般如何处理？",
  "answer": "……",
  "session_id": "demo-rag",
  "sources": [
    {
      "source": "感冒诊疗指南.txt",
      "category": "general",
      "content": "命中的文档片段",
      "score": 0.81,
      "rerank_score": 0.77,
      "page": null,
      "chunk_id": "chunk_xxx",
      "retrieval_methods": ["vector", "keyword"]
    }
  ],
  "tool_calls": [],
  "tool_calls_count": 0,
  "debug_info": {
    "requested_k": 5,
    "applied_category": "general",
    "retrieval_count": 1,
    "used_chat_mode": false,
    "low_confidence": false,
    "retrieval_strategy": "hybrid",
    "vector_result_count": 3,
    "keyword_result_count": 2,
    "merged_result_count": 4
  }
}
```

## 知识库操作示例

### 导入整个目录

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" ^
  -H "Content-Type: application/json" ^
  -d "{\"data_dir\":\"data/medical_docs\",\"category\":\"general\"}"
```

### 导入单个文件

```bash
curl -X POST "http://localhost:8000/api/v1/ingest-file?filepath=data/medical_docs/general/感冒诊疗指南.txt&category=general"
```

### 增量更新

```bash
curl -X POST "http://localhost:8000/api/v1/update/incremental"
```

### 获取统计

```bash
curl "http://localhost:8000/api/v1/stats"
```

## 前端功能概览

前端当前已经实现这些能力：

- 聊天页
  - Agent / RAG 模式切换
  - 流式回答
  - 工具调用展示
  - 来源片段展示
- 知识库页
  - 文件上传
  - 一键增量更新
  - 文件搜索
  - 状态筛选
  - 操作日志
- 设置页
  - `top_k`
  - 问答模式
  - 检索分类
  - 是否流式输出
  - 是否显示工具调用

## 测试说明

项目里的测试分成两类。

### 1. 不强依赖完整外部服务的定向测试

这些更适合先跑：

- `tests/test_retrieval_pipeline.py`
- `tests/test_knowledge_base_update.py`
- `tests/test_file_upload_service.py`
- `tests/test_file_list_status.py`
- `tests/test_rag_stats.py`

### 2. 依赖外部服务或真实环境的测试

- `tests/test_api.py`
  - 需要后端已启动
- `tests/test_complete.py`
  - 需要后端已启动
- `tests/test_agent.py`
  - 需要 Ollama，通常还要有可用知识库
- `tests/test_memory_integration.py`
  - 需要 PostgreSQL 可用

### 运行方式

```bash
python tests/run_tests.py
```

也可以单独执行：

```bash
python tests/test_frontend.py
python tests/test_api.py
python tests/test_agent.py
```

## 常用配置项

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://myuser:mypassword@192.168.150.100:5432/medical_rag` | PostgreSQL 连接串 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `EMBEDDING_MODEL` | `bag-m3:latest` | 嵌入模型 |
| `LLM_MODEL` | `qwen2.5:7b` | 对话模型 |
| `CHUNK_SIZE` | `500` | 文本块大小 |
| `CHUNK_OVERLAP` | `50` | 文本块重叠 |
| `TOP_K` | `5` | 默认召回数 |
| `API_HOST` | `0.0.0.0` | API 监听地址 |
| `API_PORT` | `8000` | API 端口 |
| `DEBUG` | `True` | 调试模式 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## 已知注意事项

这些是基于当前代码状态整理出来的，写 README 时特意按真实实现保留了：

- 文件上传接口需要 `python-multipart`
  - 当前 `requirements.txt` 没有显式声明
- `update/full` 虽然有 `clear_first` 参数，但当前清空逻辑还是占位，没有真正清空现有向量数据
- 前端里有一些偏展示性的设置项，真正影响后端行为的主要还是 `query_mode`、`query_category`、`top_k`、`enable_streaming`、`show_tool_calls`
- 默认数据库地址不是 localhost，请务必修改 `.env`

## 开发建议

如果你准备继续迭代这个项目，优先级比较高的方向通常是：

1. 给数据库迁移补上 Alembic
2. 把 `python-multipart` 纳入依赖
3. 为 `update/full(clear_first=True)` 实现真实清库
4. 为前端设置项补齐和后端配置的联动
5. 给检索与记忆链路增加更多集成测试

## 免责声明

本项目仅用于学习、演示和研究，不能替代医生的专业判断与正式诊疗意见。
