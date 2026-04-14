"""知识库管理路由"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from api.schemas import (
    IngestRequest,
    IngestResponse,
    StatsResponse,
    DeleteDocumentsRequest,
    DeleteDocumentsResponse,
    LifecycleDeleteRequest,
    RollbackRequest,
    RollbackResponse,
    FileVersionListResponse,
    IngestJobListResponse,
)
from rag.knowledge_base_update import KnowledgeBaseUpdateService
from loguru import logger

router = APIRouter(tags=["知识库"])

_kb_service = None

def get_kb_service():
    """懒加载知识库服务"""
    global _kb_service
    if _kb_service is None:
        from rag.rag_chain import MedicalRAGChain
        _kb_service = KnowledgeBaseUpdateService(MedicalRAGChain())
    return _kb_service

@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(request: IngestRequest = None):
    """导入文档"""
    try:
        if request is None:
            request = IngestRequest()
        kb_service = get_kb_service()
        result = kb_service.incremental_update(
            data_dir=request.data_dir,
            category=request.category
        )
        return IngestResponse(**result)
    except Exception as e:
        logger.error(f"导入失败: {e}")
        raise HTTPException(500, str(e))

@router.post("/ingest-file", response_model=IngestResponse)
async def ingest_file(filepath: str, category: str = "general"):
    """导入单个文件"""
    try:
        kb_service = get_kb_service()
        result = kb_service.update_single_file(filepath, category)
        return IngestResponse(**result)
    except Exception as e:
        logger.error(f"文件导入失败: {e}")
        raise HTTPException(500, str(e))

@router.post("/update/incremental", response_model=IngestResponse)
async def incremental_update(data_dir: str = None, category: str = "general"):
    """增量更新"""
    try:
        kb_service = get_kb_service()
        result = kb_service.incremental_update(data_dir, category)
        return IngestResponse(**result)
    except Exception as e:
        logger.error(f"增量更新失败: {e}")
        raise HTTPException(500, str(e))

@router.post("/update/full", response_model=IngestResponse)
async def full_update(data_dir: str = None, category: str = "general", clear_first: bool = False):
    """全量更新"""
    try:
        kb_service = get_kb_service()
        result = kb_service.full_update(data_dir, category, clear_first)
        return IngestResponse(**result)
    except Exception as e:
        logger.error(f"全量更新失败: {e}")
        raise HTTPException(500, str(e))

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """统计信息"""
    try:
        kb_service = get_kb_service()
        stats = kb_service.rag_chain.get_collection_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(500, str(e))

@router.post("/documents/delete", response_model=DeleteDocumentsResponse)
async def delete_documents(request: DeleteDocumentsRequest):
    """删除文档"""
    try:
        kb_service = get_kb_service()
        success = kb_service.rag_chain.delete_documents(request.doc_ids)
        return DeleteDocumentsResponse(
            success=success,
            message=f"删除{len(request.doc_ids)}个文档" if success else "删除失败",
            deleted_records=len(request.doc_ids) if success else 0,
            deleted_chunks=len(request.doc_ids) if success else 0,
        )
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(500, str(e))


@router.post("/documents/delete-by-rule", response_model=DeleteDocumentsResponse)
async def delete_documents_by_rule(request: LifecycleDeleteRequest):
    """按文件/分类/版本等治理维度删除知识库内容"""
    try:
        kb_service = get_kb_service()
        result = kb_service.delete_by_rule(
            source_id=request.source_id,
            category=request.category,
            source=request.source,
            version=request.version,
        )
        return DeleteDocumentsResponse(**result)
    except Exception as e:
        logger.error(f"治理删除失败: {e}")
        raise HTTPException(500, str(e))


@router.post("/documents/rollback", response_model=RollbackResponse)
async def rollback_document(request: RollbackRequest):
    """回滚到指定文件版本"""
    try:
        kb_service = get_kb_service()
        result = kb_service.rollback_file(
            source_id=request.source_id,
            target_version=request.target_version,
        )
        return RollbackResponse(**result)
    except Exception as e:
        logger.error(f"回滚文件失败: {e}")
        raise HTTPException(500, str(e))


@router.get("/documents/{source_id}/versions", response_model=FileVersionListResponse)
async def get_document_versions(source_id: str):
    """查询指定逻辑文件的全部版本历史"""
    try:
        kb_service = get_kb_service()
        versions = kb_service.list_versions(source_id)
        return FileVersionListResponse(
            source_id=source_id,
            total=len(versions),
            versions=versions,
        )
    except Exception as e:
        logger.error(f"获取文件版本历史失败: {e}")
        raise HTTPException(500, str(e))


@router.get("/ingest-jobs", response_model=IngestJobListResponse)
async def get_ingest_jobs(status: Optional[str] = None, limit: int = 20):
    """查询知识库导入任务日志"""
    try:
        kb_service = get_kb_service()
        jobs = kb_service.list_ingest_jobs(status=status, limit=limit)
        return IngestJobListResponse(total=len(jobs), jobs=jobs)
    except Exception as e:
        logger.error(f"获取知识库导入任务失败: {e}")
        raise HTTPException(500, str(e))
