"""
数据库连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy import inspect, text
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


def _upgrade_conversation_history_schema():
    """
    轻量升级 conversation_history 表结构

    当前项目没有 Alembic，这里用幂等 ALTER TABLE 保证老环境可平滑新增字段。
    """
    inspector = inspect(engine)
    if "conversation_history" not in inspector.get_table_names():
        return

    upgrade_sql = [
        "ALTER TABLE conversation_history ADD COLUMN IF NOT EXISTS tools_used TEXT",
        "ALTER TABLE conversation_history ADD COLUMN IF NOT EXISTS record_type VARCHAR(50) DEFAULT 'chat' NOT NULL",
        "ALTER TABLE conversation_history ADD COLUMN IF NOT EXISTS memory_metadata TEXT",
    ]

    with engine.begin() as conn:
        for sql in upgrade_sql:
            conn.execute(text(sql))

    logger.info("conversation_history 表结构检查完成")


def _upgrade_memory_schema():
    """
    轻量检查分层记忆相关表结构

    目前事实记忆和摘要记忆是新增表，create_all 已可完成创建。
    这里保留日志入口，便于后续继续扩展幂等升级逻辑。
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    logger.info(
        "记忆分层表结构检查完成: patient_fact_memory={}, conversation_summary={}",
        "patient_fact_memory" in table_names,
        "conversation_summary" in table_names,
    )


def _upgrade_knowledge_governance_schema():
    """
    轻量检查知识库治理相关表结构

    第6步新增的文件版本表和导入任务表由 create_all 创建。
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    logger.info(
        "知识库治理表结构检查完成: knowledge_base_files={}, knowledge_base_ingest_jobs={}",
        "knowledge_base_files" in table_names,
        "knowledge_base_ingest_jobs" in table_names,
    )


def init_db():
    """初始化数据库，创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        _upgrade_conversation_history_schema()
        _upgrade_memory_schema()
        _upgrade_knowledge_governance_schema()
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
