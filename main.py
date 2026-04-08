"""
FastAPI应用主文件
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database.connection import init_db
from api.routes import router
from loguru import logger
import sys


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info("=" * 50)
    logger.info("医疗RAG问答系统启动中...")
    logger.info("=" * 50)
    
    # 初始化数据库
    try:
        init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
    
    logger.info("系统启动完成")
    logger.info(f"API文档地址: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    
    yield
    
    # 关闭事件
    logger.info("医疗RAG问答系统关闭中...")
    logger.info("系统已关闭")

# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/medical_rag_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.LOG_LEVEL
)

# 创建FastAPI应用
app = FastAPI(
    title="医疗RAG问答系统",
    description="基于LangChain和Ollama的医疗文档检索增强生成系统",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用医疗RAG问答系统",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"启动服务器: {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
