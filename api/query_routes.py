"""问答相关路由 - Agent模式"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
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
            thread_id=request.session_id or "default"
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query-stream")
async def query_stream(request: QueryRequest):
    """流式问答"""
    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': 'Agent开始处理'}, ensure_ascii=False)}\n\n"

            for event in medical_agent.stream_query(
                    request.question,
                    request.session_id or "default"
            ):
                yield format_agent_event(event)

            yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

def format_agent_event(event) -> str:
    """格式化Agent事件为SSE"""
    try:
        if isinstance(event, dict):
            if "messages" in event:
                messages = event["messages"]
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        tool_info = []
                        for tc in last_msg.tool_calls:
                            tool_info.append({
                                "name": tc.get("name", "unknown"),
                                "args": tc.get("args", {})
                            })
                        return f"data: {json.dumps({'type': 'tool_call', 'tools': tool_info}, ensure_ascii=False)}\n\n"
                    elif hasattr(last_msg, 'content') and last_msg.content:
                        return f"data: {json.dumps({'type': 'content', 'content': last_msg.content}, ensure_ascii=False)}\n\n"
            elif "agent" in event:
                return f"data: {json.dumps({'type': 'thinking'}, ensure_ascii=False)}\n\n"
        return f"data: {json.dumps({'type': 'content', 'content': str(event)}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"事件格式化失败: {e}")
        return f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
