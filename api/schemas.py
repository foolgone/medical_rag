"""
Pydantic模型定义
用于API请求和响应的数据验证
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class QueryRequest(BaseModel):
    """查询请求模型"""
    question: str = Field(..., description="用户问题", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话ID")
    k: Optional[int] = Field(None, description="检索文档数量", ge=1, le=20)
    category: Optional[str] = Field(None, description="文档分类过滤")


class QueryResponse(BaseModel):
    """查询响应模型"""
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="AI回答")
    context_count: int = Field(..., description="参考文档数量")
    sources: List[Dict] = Field(default_factory=list, description="来源文档列表")


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


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
