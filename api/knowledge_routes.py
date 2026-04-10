"""知识库管理路由"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from api.schemas import IngestRequest, IngestResponse, StatsResponse, DeleteDocumentsRequest, DeleteDocumentsResponse
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
        count = kb_service.rag_chain.ingest_documents(
            data_dir=request.data_dir,
            category=request.category
        )
        return IngestResponse(success=True, ingested_count=count, message=f"导入{count}个文档块")
    except Exception as e:
        logger.error(f"导入失败: {e}")
        raise HTTPException(500, str(e))

@router.post("/ingest-file", response_model=IngestResponse)
async def ingest_file(filepath: str, category: str = "general"):
    """导入单个文件"""
    try:
        kb_service = get_kb_service()
        rag_chain = kb_service.rag_chain
        documents, is_new = rag_chain.document_loader.load_single_file(filepath)
        if not documents:
            return IngestResponse(success=False, ingested_count=0, message="文件加载失败")
        documents = rag_chain.document_loader.add_metadata(documents, category)
        split_docs = rag_chain.text_splitter.split_documents(documents)
        doc_ids = rag_chain.vector_store.add_documents(split_docs)
        return IngestResponse(success=True, ingested_count=len(doc_ids), message=f"导入{len(doc_ids)}个文档块")
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
            message=f"删除{len(request.doc_ids)}个文档" if success else "删除失败"
        )
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(500, str(e))
