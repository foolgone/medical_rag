"""问答相关路由 - Agent模式"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.schemas import QueryRequest, QueryResponse, HealthResponse
from agents.medical_agent import medical_agent
from loguru import logger
import json

router = APIRouter(tags=["问答"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(status="healthy", version="2.0.0-Agent")

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """标准问答"""
    try:
        logger.info(f"收到查询: {request.question[:50]}...")
        result = medical_agent.query(
            question=request.question,
            thread_id=request.session_id or "default",
            k=request.k,
            category=request.category
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query-rag", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """RAG标准问答"""
    try:
        logger.info(f"收到RAG查询: {request.question[:50]}...")
        result = medical_agent.rag_chain.query(
            question=request.question,
            session_id=request.session_id or "default",
            k=request.k,
            filter_dict=medical_agent.rag_chain.build_filter_dict(request.category)
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"RAG查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query-stream")
async def query_stream(request: QueryRequest):
    """流式问答"""
    async def generate():
        try:
            for event in medical_agent.stream_query(
                question=request.question,
                thread_id=request.session_id or "default",
                k=request.k,
                category=request.category
            ):
                yield format_agent_event(event)
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.post("/query-stream-rag")
async def query_stream_rag(request: QueryRequest):
    """RAG流式问答"""
    async def generate():
        try:
            async for event in medical_agent.rag_chain.stream_query(
                question=request.question,
                session_id=request.session_id or "default",
                k=request.k,
                filter_dict=medical_agent.rag_chain.build_filter_dict(request.category)
            ):
                yield format_agent_event(event)
        except Exception as e:
            logger.error(f"RAG流式生成失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

def format_agent_event(event) -> str:
    """格式化Agent事件为SSE"""
    try:
        payload = event if isinstance(event, dict) else {"type": "content", "content": str(event)}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"事件格式化失败: {e}")
        return f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
