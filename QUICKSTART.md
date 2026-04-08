# 医疗RAG问答系统 - 快速启动指南

## 📋 项目概述

这是一个基于LangChain、Ollama和PostgreSQL构建的医疗文档检索增强生成（RAG）系统。

### 核心功能
- ✅ 医疗文档导入和管理（支持PDF、Word、TXT格式）
- ✅ 智能语义检索
- ✅ 基于上下文的问答生成
- ✅ 对话历史保存
- ✅ RESTful API接口
- ✅ 完整的日志记录

## 🏗️ 技术栈

- **框架**: LangChain 1.x, FastAPI
- **LLM**: Ollama (llama3.1)
- **嵌入模型**: Ollama (nomic-embed-text)
- **向量数据库**: PostgreSQL + pgvector
- **数据验证**: Pydantic
- **Python版本**: 3.11+

## 📁 项目结构

```
PythonProject/
├── api/                    # API模块
│   ├── __init__.py
│   ├── routes.py          # API路由
│   └── schemas.py         # Pydantic模型
├── database/              # 数据库模块
│   ├── __init__.py
│   ├── connection.py      # 数据库连接
│   └── models.py          # 数据模型
├── rag/                   # RAG核心模块
│   ├── __init__.py
│   ├── document_loader.py # 文档加载器
│   ├── text_splitter.py   # 文本分割器
│   ├── vector_store.py    # 向量存储
│   ├── retriever.py       # 检索器
│   └── rag_chain.py       # RAG链
├── llm/                   # LLM模块
│   ├── __init__.py
│   └── ollama_client.py   # Ollama客户端
├── data/                  # 数据目录
│   └── medical_docs/      # 医疗文档
│       ├── 感冒诊疗指南.txt
│       ├── 高血压管理指南.txt
│       └── 糖尿病饮食管理.txt
├── config.py              # 配置文件
├── main.py                # 主入口
├── requirements.txt       # 依赖包
├── setup.py               # 初始化脚本
├── .env.example           # 环境变量示例
└── .gitignore            # Git忽略文件
```

## 🚀 快速开始

### 步骤1: 环境准备

#### 1.1 安装Python 3.11+
确保系统已安装Python 3.11或更高版本。

#### 1.2 安装Ollama
1. 下载并安装Ollama: https://ollama.com
2. 启动Ollama服务:
   ```bash
   ollama serve
   ```
3. 拉取所需模型:
   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3.1
   ```

#### 1.3 安装PostgreSQL
1. 安装PostgreSQL数据库
2. 安装pgvector扩展:
   ```sql
   CREATE EXTENSION vector;
   ```
3. 创建数据库:
   ```sql
   CREATE DATABASE medical_rag_db;
   ```

### 步骤2: 项目初始化

#### 方式一: 使用初始化脚本（推荐）
```bash
python setup.py
```

#### 方式二: 手动安装
```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 复制环境变量文件
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# 5. 编辑.env文件，配置数据库连接等信息
```

### 步骤3: 配置环境变量

编辑 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/medical_rag_db

# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
LLM_MODEL=llama3.1

# RAG配置
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=5

# API配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# 日志配置
LOG_LEVEL=INFO
```

### 步骤4: 启动应用

```bash
python main.py
```

应用启动后，访问:
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health

## 📖 API使用指南

### 1. 导入文档

**请求:**
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "data_dir": "data/medical_docs",
    "category": "general"
  }'
```

**响应:**
```json
{
  "success": true,
  "ingested_count": 45,
  "message": "成功导入 45 个文档块"
}
```

### 2. 问答查询

**请求:**
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "感冒了应该吃什么药？",
    "session_id": "session_001",
    "k": 5
  }'
```

**响应:**
```json
{
  "question": "感冒了应该吃什么药？",
  "answer": "根据医学指南，感冒治疗以对症治疗为主...",
  "context_count": 5,
  "sources": [
    {
      "content": "常用药物包括解热镇痛药...",
      "source": "感冒诊疗指南.txt",
      "category": "general"
    }
  ]
}
```

### 3. 获取统计信息

**请求:**
```bash
curl -X GET "http://localhost:8000/api/v1/stats"
```

**响应:**
```json
{
  "collection_name": "medical_documents",
  "embedding_model": "nomic-embed-text",
  "llm_model": "llama3.1",
  "top_k": 5
}
```

### 4. 删除文档

**请求:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": ["doc_id_1", "doc_id_2"]
  }'
```

## 🔧 配置说明

### 修改文本分块大小
在 `.env` 文件中调整:
```env
CHUNK_SIZE=500        # 每个文本块的大小
CHUNK_OVERLAP=50      # 文本块重叠大小
```

### 修改检索数量
```env
TOP_K=5              # 每次检索返回的文档数量
```

### 更换模型
```env
EMBEDDING_MODEL=nomic-embed-text   # 嵌入模型
LLM_MODEL=llama3.1                 # LLM模型
```

## 📝 添加自定义医疗文档

1. 将文档放入 `data/medical_docs/` 目录
2. 支持的格式: PDF, Word (.docx), TXT
3. 通过API导入:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingest" \
     -H "Content-Type: application/json" \
     -d '{"data_dir": "data/medical_docs", "category": "custom"}'
   ```

## 🐛 常见问题

### 1. Ollama连接失败
**问题**: `Connection refused` 或 `500 error`

**解决**:
- 确认Ollama服务已启动: `ollama serve`
- 检查模型是否已下载: `ollama list`
- 验证服务地址: `http://localhost:11434`

### 2. 数据库连接失败
**问题**: `could not connect to server`

**解决**:
- 确认PostgreSQL服务已启动
- 检查`.env`中的数据库配置
- 确认pgvector扩展已安装

### 3. 导入文档失败
**问题**: 文档导入时出错

**解决**:
- 检查文档格式是否支持
- 确认文档路径正确
- 查看日志文件 `logs/` 获取详细错误信息

### 4. 回答质量不佳
**优化建议**:
- 增加相关文档数量
- 调整 `TOP_K` 参数
- 优化文档质量和相关性
- 尝试不同的LLM模型

## 📊 日志查看

日志文件位于 `logs/` 目录:
```bash
# 查看最新日志
tail -f logs/medical_rag_*.log
```

## 🔐 生产环境部署建议

1. **安全配置**
   - 修改默认端口
   - 启用HTTPS
   - 配置CORS白名单
   - 添加API认证

2. **性能优化**
   - 调整数据库连接池大小
   - 启用缓存机制
   - 使用GPU加速嵌入计算

3. **监控告警**
   - 集成Prometheus监控
   - 配置日志聚合
   - 设置异常告警

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请提交GitHub Issue。
