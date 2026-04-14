"""
项目配置文件
使用Pydantic Settings管理配置项
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""
    
    # 数据库配置
    DATABASE_URL: str
    
    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "bge-m3:latest"
    LLM_MODEL: str = "qwen2.5:7b"
    
    # RAG配置
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    LOW_CONFIDENCE_THRESHOLD: float = 0.35

    # 评估配置
    EVAL_DATA_DIR: str = "eval"
    EVAL_API_TIMEOUT_SEC: float = 60.0
    
    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # 第9步：缓存/并发/可观测性（MVP）
    ENABLE_STATS_CACHE: bool = True
    STATS_CACHE_TTL_SEC: int = 15

    API_MAX_CONCURRENT_QUERIES: int = 4
    API_MAX_CONCURRENT_STREAMS: int = 2
    API_CONCURRENCY_ACQUIRE_TIMEOUT_SEC: float = 0.01
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# 创建全局配置实例
try:
    settings = Settings()
except ValidationError as e:
    raise RuntimeError(
        "配置加载失败：缺少必要环境变量。\n"
        "请执行：复制 .env.example 为 .env，并至少设置 DATABASE_URL。\n"
        "示例：DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/medical_rag\n"
        f"详细校验错误：{e}"
    ) from e
