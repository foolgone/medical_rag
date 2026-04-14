"""
数据库模型定义
使用PostgreSQL + pgvector存储向量嵌入
"""
from sqlalchemy import Column, Float, Integer, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class MedicalDocument(Base):
    """医疗文档表"""
    __tablename__ = "medical_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, comment="文档标题")
    content = Column(Text, nullable=False, comment="文档内容")
    source = Column(String(1000), comment="文档来源")
    category = Column(String(200), comment="文档分类")
    embedding = Column(Vector(768), comment="向量嵌入")  # nomic-embed-text 维度为768
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<MedicalDocument(id={self.id}, title='{self.title}')>"


class ConversationHistory(Base):
    """对话历史表"""
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True, comment="会话ID")
    question = Column(Text, nullable=False, comment="用户问题")
    answer = Column(Text, nullable=False, comment="AI回答")
    context = Column(Text, comment="检索的上下文")
    tools_used = Column(Text, comment="工具调用摘要")
    record_type = Column(String(50), nullable=False, server_default="chat", comment="记录类型")
    memory_metadata = Column(Text, comment="额外记忆元数据")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    def __repr__(self):
        return f"<ConversationHistory(id={self.id}, session_id='{self.session_id}')>"


class PatientFactMemory(Base):
    """患者事实记忆表"""
    __tablename__ = "patient_fact_memory"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True, comment="会话ID")
    fact_type = Column(String(50), nullable=False, index=True, comment="事实类型")
    fact_key = Column(String(100), nullable=False, index=True, comment="事实键")
    fact_value = Column(Text, nullable=False, comment="事实值")
    confidence = Column(Float, nullable=False, server_default="0.8", comment="置信度")
    source = Column(String(50), nullable=False, server_default="user_explicit", comment="来源")
    status = Column(String(20), nullable=False, server_default="active", comment="状态")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return (
            f"<PatientFactMemory(id={self.id}, session_id='{self.session_id}', "
            f"fact_key='{self.fact_key}', status='{self.status}')>"
        )


class ConversationSummary(Base):
    """阶段摘要记忆表"""
    __tablename__ = "conversation_summary"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True, comment="会话ID")
    start_history_id = Column(Integer, nullable=False, comment="摘要起始历史ID")
    end_history_id = Column(Integer, nullable=False, comment="摘要结束历史ID")
    summary_text = Column(Text, nullable=False, comment="摘要内容")
    summary_type = Column(String(50), nullable=False, server_default="stage", comment="摘要类型")
    message_count = Column(Integer, nullable=False, server_default="0", comment="覆盖轮次数")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return (
            f"<ConversationSummary(id={self.id}, session_id='{self.session_id}', "
            f"range={self.start_history_id}-{self.end_history_id})>"
        )
