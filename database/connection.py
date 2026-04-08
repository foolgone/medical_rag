"""
数据库连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config import settings
from database.models import Base
from loguru import logger


# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise


@contextmanager
def get_db_session() -> Session:
    """获取数据库会话的上下文管理器"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI依赖注入使用的数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
