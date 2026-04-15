"""
数据库模型定义
使用PostgreSQL + pgvector存储向量嵌入
"""
from sqlalchemy import Boolean, Column, Float, Integer, String, Text, DateTime, func
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
    embedding = Column(Vector(768), comment="向量嵌入（维度取决于所用 embedding 模型）")
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


class KnowledgeBaseFile(Base):
    """知识库文件生命周期表"""
    __tablename__ = "knowledge_base_files"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String(64), nullable=False, index=True, comment="逻辑源文件ID")
    filename = Column(String(500), nullable=False, comment="当前文件名")
    filepath = Column(String(1000), nullable=False, index=True, comment="文件物理路径")
    logical_name = Column(String(500), nullable=False, comment="逻辑文件名")
    category = Column(String(200), nullable=False, index=True, comment="文档分类")
    source_type = Column(String(50), nullable=False, comment="文件类型")
    file_hash = Column(String(64), nullable=False, index=True, comment="文件哈希")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    status = Column(String(30), nullable=False, default="active", index=True, comment="状态")
    is_current = Column(Boolean, nullable=False, default=True, comment="是否当前有效版本")
    chunk_count = Column(Integer, nullable=False, default=0, comment="向量块数量")
    vector_ids = Column(Text, comment="向量文档ID列表(JSON)")
    error_message = Column(Text, comment="失败原因")
    uploaded_at = Column(DateTime, server_default=func.now(), comment="上传时间")
    ingested_at = Column(DateTime, comment="入库时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return (
            f"<KnowledgeBaseFile(id={self.id}, source_id='{self.source_id}', "
            f"version={self.version}, status='{self.status}')>"
        )


class SessionToken(Base):
    """会话令牌表"""
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True, comment="会话ID")
    token_hash = Column(String(64), nullable=False, comment="令牌哈希（SHA-256）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    last_used_at = Column(DateTime, server_default=func.now(), comment="最近使用时间")

    def __repr__(self):
        return f"<SessionToken(session_id='{self.session_id}')>"


class KnowledgeBaseIngestJob(Base):
    """知识库导入任务日志表"""
    __tablename__ = "knowledge_base_ingest_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(30), nullable=False, index=True, comment="任务类型")
    status = Column(String(30), nullable=False, index=True, comment="任务状态")
    source_id = Column(String(64), index=True, comment="逻辑源文件ID")
    file_id = Column(Integer, index=True, comment="关联文件记录ID")
    file_hash = Column(String(64), index=True, comment="文件哈希")
    version = Column(Integer, comment="版本号")
    chunk_count = Column(Integer, nullable=False, default=0, comment="入库块数")
    message = Column(Text, comment="结果消息")
    started_at = Column(DateTime, server_default=func.now(), comment="开始时间")
    finished_at = Column(DateTime, comment="结束时间")

    def __repr__(self):
        return (
            f"<KnowledgeBaseIngestJob(id={self.id}, job_type='{self.job_type}', "
            f"status='{self.status}')>"
        )
