"""
数据库模型定义
使用PostgreSQL + pgvector存储向量嵌入
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
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
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    def __repr__(self):
        return f"<ConversationHistory(id={self.id}, session_id='{self.session_id}')>"
