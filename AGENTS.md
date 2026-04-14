# 仓库指南

## 项目结构与模块组织
`main.py` 是 FastAPI 后端入口，并注册 `api/` 下的路由。核心检索与生成逻辑位于 `rag/`，LLM 集成位于 `llm/`，数据库初始化与模型位于 `database/`，Agent 编排位于 `agents/`，工具封装位于 `tools/`。Streamlit 前端入口为 `app_streamlit.py`，模块化界面代码集中在 `app/components/`、`app/pages/` 和 `app/widgets/`。测试脚本位于 `tests/`，示例医疗文档位于 `data/medical_docs/`，界面或说明图片位于 `images/`。

## 构建、测试与开发命令
先创建虚拟环境并安装依赖：`python -m venv .venv`、`.venv\Scripts\activate`、`pip install -r requirements.txt`。如果需要交互式初始化，可运行 `python setup.py`，它会帮助创建目录并生成 `.env`。启动后端使用 `python main.py`，启动前端使用 `python -m streamlit run app_streamlit.py`。运行整套脚本测试可执行 `python tests/run_tests.py`，也可以单独运行 `python tests/test_frontend.py` 或 `python tests/test_api.py`。

## 代码风格与命名规范
遵循现有 Python 风格：4 空格缩进，模块和函数使用 `snake_case`，类使用 `PascalCase`，公共函数保留简短 docstring。保持模块职责单一，本仓库倾向于小而明确的文件，例如 `app/components/chat_area/chat_input.py`。在合适的地方补充类型标注，并将配置集中放在 `config.py` 或 `app/config.py`。仓库当前未提交格式化或 lint 配置，因此提交前请按 PEP 8 和周边代码风格保持一致。

## 测试指南
测试主要是可直接执行的 Python 脚本，命名模式为 `tests/test_*.py`。`tests/test_frontend.py` 主要验证本地对象装配；`tests/test_api.py` 和 `tests/test_complete.py` 依赖已启动的后端服务 `http://localhost:8000`。`tests/test_agent.py` 还可能依赖 Ollama、PostgreSQL 以及已导入的 RAG 数据。新增测试时请放在 `tests/` 中并使用清晰命名，同时在测试文件头部或 PR 描述中注明所需外部服务。

## 提交与合并请求规范
最近的提交历史采用简短的约定式前缀，例如 `feat(file-upload):`、`refactor(chat):`、`docs(readme):`，后续提交也应保持这一模式。每次提交只聚焦一个改动主题。PR 需要包含简洁摘要、必要的 `.env` 或服务前置条件、实际执行过的命令，以及涉及 Streamlit 界面变更时的截图。

## 安全与配置提示
从 `.env.example` 复制生成 `.env`，不要将密钥、数据库连接串或主机相关配置提交到 Git。运行依赖服务的测试前，请确认 Ollama 在 `OLLAMA_BASE_URL` 可访问，且 PostgreSQL/pgvector 配置与 `DATABASE_URL` 一致。
