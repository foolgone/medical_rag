"""
项目配置文件
使用Pydantic Settings管理配置项
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://myuser:mypassword@192.168.150.100:5432/medical_rag"
    
    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "bag-m3:latest"
    LLM_MODEL: str = "qwen2.5:7b"
    
    # RAG配置
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    
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
settings = Settings()
