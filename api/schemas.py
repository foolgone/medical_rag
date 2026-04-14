"""
Pydantic模型定义
用于API请求和响应的数据验证
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """查询请求模型"""
    question: str = Field(..., description="用户问题", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话ID")
    k: Optional[int] = Field(None, description="检索文档数量", ge=1, le=20)
    category: Optional[str] = Field(None, description="文档分类过滤")


class SourceItem(BaseModel):
    """问答来源项"""
    source: str = Field(..., description="来源文件名")
    category: Optional[str] = Field(None, description="文档分类")
    content: Optional[str] = Field(None, description="命中文档片段")
    score: Optional[float] = Field(None, description="检索分数")
    raw_score: Optional[float] = Field(None, description="原始检索距离分数")
    keyword_score: Optional[float] = Field(None, description="关键词检索分数")
    rerank_score: Optional[float] = Field(None, description="重排后的融合分数")
    page: Optional[int] = Field(None, description="页码")
    chunk_id: Optional[str] = Field(None, description="文档块ID")
    source_type: Optional[str] = Field(None, description="来源文件类型")
    updated_at: Optional[str] = Field(None, description="文档更新时间")
    retrieval_methods: List[str] = Field(default_factory=list, description="命中的检索方式")


class ToolCallItem(BaseModel):
    """工具调用信息"""
    name: str = Field(..., description="工具名称")
    args: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class QueryDebugInfo(BaseModel):
    """问答调试信息"""
    requested_k: Optional[int] = Field(None, description="请求的检索数量")
    applied_category: Optional[str] = Field(None, description="实际应用的分类过滤")
    retrieval_count: int = Field(0, description="实际命中文档数量")
    used_chat_mode: bool = Field(False, description="是否未命中知识库")
    low_confidence: bool = Field(False, description="是否为低置信命中")
    best_score: Optional[float] = Field(None, description="最佳匹配分数")
    fallback_reason: Optional[str] = Field(None, description="降级原因")
    retrieval_strategy: Optional[str] = Field(None, description="检索策略")
    vector_result_count: int = Field(0, description="向量召回候选数")
    keyword_result_count: int = Field(0, description="关键词召回候选数")
    merged_result_count: int = Field(0, description="融合后的候选数")
    rewritten_query: Optional[str] = Field(None, description="查询改写结果")
    memory_applied: bool = Field(False, description="是否注入了历史记忆")
    memory_message_count: int = Field(0, description="注入的历史消息数量")
    fact_memory_count: int = Field(0, description="注入的事实记忆数量")
    summary_memory_applied: bool = Field(False, description="是否注入了摘要记忆")


class QueryResponse(BaseModel):
    """查询响应模型"""
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="AI回答")
    session_id: Optional[str] = Field(None, description="会话ID")
    sources: List[SourceItem] = Field(default_factory=list, description="来源文档列表")
    tool_calls: List[ToolCallItem] = Field(default_factory=list, description="工具调用列表")
    tool_calls_count: int = Field(0, description="工具调用次数")
    debug_info: QueryDebugInfo = Field(default_factory=QueryDebugInfo, description="调试信息")


class IngestRequest(BaseModel):
    """文档导入请求模型"""
    data_dir: Optional[str] = Field("data/medical_docs", description="文档目录")
    category: Optional[str] = Field("general", description="文档分类")


class IngestResponse(BaseModel):
    """文档导入响应模型"""
    success: bool = Field(..., description="是否成功")
    ingested_count: int = Field(..., description="导入的文档数量")
    message: str = Field(..., description="提示信息")


class DeleteDocumentsRequest(BaseModel):
    """删除文档请求模型"""
    doc_ids: List[str] = Field(..., description="要删除的文档ID列表")


class DeleteDocumentsResponse(BaseModel):
    """删除文档响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")


class StatsResponse(BaseModel):
    """统计信息响应模型"""
    collection_name: str = Field(..., description="集合名称")
    embedding_model: str = Field(..., description="嵌入模型")
    llm_model: str = Field(..., description="LLM模型")
    top_k: int = Field(..., description="检索数量")
    total_files: int = Field(0, description="知识库文件总数")
    vectorized_files: int = Field(0, description="已向量化文件数")
    pending_files: int = Field(0, description="待向量化文件数")
    document_chunks: int = Field(0, description="文档块数量")
    category_count: int = Field(0, description="分类数")
    last_updated: Optional[str] = Field(None, description="最后更新时间")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")


class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    filename: str = Field(..., description="文件名")
    filepath: str = Field(..., description="文件路径")
    category: str = Field(..., description="文档分类")
    size: int = Field(..., description="文件大小（字节）")
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="提示信息")


class BatchUploadResponse(BaseModel):
    """批量上传响应模型"""
    total: int = Field(..., description="总文件数")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[FileUploadResponse] = Field(..., description="详细结果")


class FileInfo(BaseModel):
    """文件信息模型"""
    filename: str = Field(..., description="文件名")
    category: str = Field(..., description="文档分类")
    size: int = Field(..., description="文件大小（字节）")
    path: str = Field(..., description="文件路径")
    filepath: Optional[str] = Field(None, description="文件路径")
    upload_time: Optional[str] = Field(None, description="上传时间")
    status: Optional[str] = Field("pending", description="文件状态")


class FileListResponse(BaseModel):
    """文件列表响应模型"""
    files: List[FileInfo] = Field(..., description="文件列表")
    total: int = Field(..., description="文件总数")
