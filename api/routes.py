"""
API路由定义
提供RESTful API接口
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator, List
from api.schemas import (
    QueryRequest,
    QueryResponse,
    IngestRequest,
    IngestResponse,
    DeleteDocumentsRequest,
    DeleteDocumentsResponse,
    StatsResponse,
    HealthResponse,
    FileUploadResponse,
    BatchUploadResponse,
    FileListResponse,
    FileInfo
)
from rag.rag_chain import MedicalRAGChain
from rag.file_upload_service import FileUploadService
from rag.knowledge_base_update import KnowledgeBaseUpdateService
from loguru import logger
import json

router = APIRouter()

# 创建全局RAG链实例
rag_chain = MedicalRAGChain()
file_upload_service = FileUploadService()
update_service = KnowledgeBaseUpdateService(rag_chain)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    问答接口

    Args:
        request: 查询请求

    Returns:
        查询响应
    """
    try:
        logger.info(f"收到查询请求: {request.question[:50]}...")

        # 构建过滤条件
        filter_dict = None
        if request.category:
            filter_dict = {"category": request.category}

        # 执行查询
        result = rag_chain.query(
            question=request.question,
            session_id=request.session_id,
            k=request.k,
            filter_dict=filter_dict
        )

        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"查询处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")


@router.post("/query-stream")
async def query_stream(request: QueryRequest):
    """
    流式问答接口

    Args:
        request: 查询请求

    Returns:
        流式响应
    """
    try:
        logger.info(f"收到流式查询请求: {request.question[:50]}...")

        # 构建过滤条件
        filter_dict = None
        if request.category:
            filter_dict = {"category": request.category}

        async def generate_stream() -> AsyncGenerator[str, None]:
            """生成流式响应"""
            try:
                # 发送开始信号
                yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"

                # 检索文档
                docs = rag_chain.retriever.retrieve(
                    request.question,
                    k=request.k,
                    filter_dict=filter_dict
                )

                # 发送检索结果
                sources = [
                    {
                        "content": doc.page_content[:200],
                        "source": doc.metadata.get("source", "未知"),
                        "category": doc.metadata.get("category", "未知")
                    }
                    for doc in docs
                ]
                yield f"data: {json.dumps({'type': 'sources', 'count': len(docs), 'sources': sources}, ensure_ascii=False)}\n\n"

                if not docs:
                    # 聊天模式
                    logger.info("未检索到相关文档，使用聊天模式")
                    async for chunk in rag_chain.llm_client.generate_stream(
                        request.question,
                        system_prompt="""你是一个专业的医疗助手，具备丰富的医学知识。
请遵循以下原则：
1. 回答要专业、准确、易懂
2. 如果涉及具体诊断或用药，请提醒用户咨询专业医生
3. 可以用通俗易懂的语言解释医学概念
4. 提供实用的健康建议
5. 承认知识局限性，不过度自信"""
                    ):
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                else:
                    # RAG模式
                    context = rag_chain.retriever.format_context(docs)
                    
                    # 构建提示
                    system_prompt = """你是一个专业的医疗助手，基于提供的医学知识回答问题。
请遵循以下原则：
1. 只基于提供的上下文信息回答问题
2. 如果上下文中没有足够信息，请说明"根据现有资料无法确定"
3. 回答要专业、准确、易懂
4. 必要时提醒用户咨询专业医生"""
                    
                    full_prompt = f"""基于以下医学知识：

{context}

请回答这个问题：{request.question}

回答："""
                    
                    # 流式生成
                    async for chunk in rag_chain.llm_client.generate_stream(
                        full_prompt,
                        system_prompt=system_prompt
                    ):
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"

                # 发送完成信号
                yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        logger.error(f"流式查询处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"流式查询处理失败: {str(e)}")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(request: IngestRequest = None):
    """
    文档导入接口

    Args:
        request: 导入请求

    Returns:
        导入响应
    """
    try:
        logger.info(f"收到文档导入请求: {request.data_dir if request else 'default'}")

        if request is None:
            request = IngestRequest()

        # 导入文档
        count = rag_chain.ingest_documents(
            data_dir=request.data_dir,
            category=request.category
        )

        return IngestResponse(
            success=True,
            ingested_count=count,
            message=f"成功导入 {count} 个文档块"
        )
    except Exception as e:
        logger.error(f"文档导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档导入失败: {str(e)}")


@router.post("/documents/delete", response_model=DeleteDocumentsResponse)
async def delete_documents(request: DeleteDocumentsRequest):
    """
    删除文档接口

    Args:
        request: 删除请求

    Returns:
        删除响应
    """
    try:
        logger.info(f"收到删除文档请求，数量: {len(request.doc_ids)}")

        # 删除文档
        success = rag_chain.delete_documents(request.doc_ids)

        return DeleteDocumentsResponse(
            success=success,
            message=f"成功删除 {len(request.doc_ids)} 个文档" if success else "删除失败"
        )
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    获取知识库统计信息

    Returns:
        统计信息
    """
    try:
        logger.info("收到统计信息查询请求")

        stats = rag_chain.get_collection_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    category: str = "general"
):
    """
    上传单个文件接口

    Args:
        file: 上传的文件
        category: 文档分类

    Returns:
        文件信息
    """
    try:
        logger.info(f"收到文件上传请求: {file.filename}")
        result = await file_upload_service.save_uploaded_file(file, category)
        
        return FileUploadResponse(
            filename=result['filename'],
            filepath=result['filepath'],
            category=result['category'],
            size=result['size'],
            success=True,
            message=f"文件上传成功: {result['filename']}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_files_batch(
    files: List[UploadFile] = File(...),
    category: str = "general"
):
    """
    批量上传文件接口

    Args:
        files: 上传的文件列表
        category: 文档分类

    Returns:
        批量上传结果
    """
    try:
        logger.info(f"收到批量文件上传请求，数量: {len(files)}")
        results = await file_upload_service.save_multiple_files(files, category)
        
        success_count = sum(1 for r in results if r.get('success'))
        failed_count = len(results) - success_count
        
        return BatchUploadResponse(
            total=len(results),
            success_count=success_count,
            failed_count=failed_count,
            results=[FileUploadResponse(**r) for r in results if 'filepath' in r]
        )
    except Exception as e:
        logger.error(f"批量文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量文件上传失败: {str(e)}")


@router.get("/files", response_model=FileListResponse)
async def list_files(category: Optional[str] = None):
    """
    获取已上传的文件列表

    Args:
        category: 文档分类过滤

    Returns:
        文件列表
    """
    try:
        logger.info(f"获取文件列表请求, category: {category}")
        files = file_upload_service.list_uploaded_files(category)
        
        return FileListResponse(
            files=[FileInfo(**f) for f in files],
            total=len(files)
        )
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.delete("/files/{filename}", response_model=DeleteDocumentsResponse)
async def delete_file(filename: str, category: str = "general"):
    """
    删除已上传的文件

    Args:
        filename: 文件名
        category: 文档分类

    Returns:
        删除结果
    """
    try:
        logger.info(f"删除文件请求: {filename}")
        success = file_upload_service.delete_file(filename, category)
        
        return DeleteDocumentsResponse(
            success=success,
            message=f"文件删除成功: {filename}" if success else f"文件不存在: {filename}"
        )
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.post("/ingest-file", response_model=IngestResponse)
async def ingest_uploaded_file(
    filepath: str,
    category: str = "general"
):
    """
    导入已上传的文件到知识库

    Args:
        filepath: 文件路径
        category: 文档分类

    Returns:
        导入结果
    """
    try:
        logger.info(f"导入文件到知识库: {filepath}")
        
        # 加载单个文件
        documents, is_new = rag_chain.document_loader.load_single_file(filepath)
        
        if not documents:
            return IngestResponse(
                success=False,
                ingested_count=0,
                message="文件加载失败或文件已存在"
            )
        
        # 添加元数据
        documents = rag_chain.document_loader.add_metadata(documents, category)
        
        # 分割并存储
        split_docs = rag_chain.text_splitter.split_documents(documents)
        doc_ids = rag_chain.vector_store.add_documents(split_docs)
        
        return IngestResponse(
            success=True,
            ingested_count=len(doc_ids),
            message=f"成功导入 {len(doc_ids)} 个文档块"
        )
    except Exception as e:
        logger.error(f"文件导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件导入失败: {str(e)}")


@router.post("/update/incremental", response_model=IngestResponse)
async def incremental_update(data_dir: Optional[str] = None, category: str = "general"):
    """
    增量更新知识库（仅导入新文件）

    Args:
        data_dir: 文档目录
        category: 文档分类

    Returns:
        更新结果
    """
    try:
        logger.info("收到增量更新请求")
        result = update_service.incremental_update(data_dir, category)
        
        return IngestResponse(
            success=result['success'],
            ingested_count=result['ingested_count'],
            message=result['message']
        )
    except Exception as e:
        logger.error(f"增量更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"增量更新失败: {str(e)}")


@router.post("/update/full", response_model=IngestResponse)
async def full_update(data_dir: Optional[str] = None, category: str = "general", clear_first: bool = False):
    """
    全量更新知识库（重新导入所有文件）

    Args:
        data_dir: 文档目录
        category: 文档分类
        clear_first: 是否先清空现有数据

    Returns:
        更新结果
    """
    try:
        logger.info("收到全量更新请求")
        result = update_service.full_update(data_dir, category, clear_first)
        
        return IngestResponse(
            success=result['success'],
            ingested_count=result['ingested_count'],
            message=result['message']
        )
    except Exception as e:
        logger.error(f"全量更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"全量更新失败: {str(e)}")

