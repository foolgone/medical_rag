"""问答相关路由 - Agent模式"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from functools import partial
from urllib.error import URLError
from urllib.request import urlopen

import anyio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.schemas import HealthCheckItem, HealthResponse, QueryRequest, QueryResponse
from api.session_routes import verify_session_token
from agents.medical_agent import medical_agent
from config import settings
from database.connection import engine
from loguru import logger
from sqlalchemy import text

router = APIRouter(tags=["问答"])


_QUERY_SEMAPHORE = asyncio.Semaphore(getattr(settings, "API_MAX_CONCURRENT_QUERIES", 4))
_STREAM_SEMAPHORE = asyncio.Semaphore(getattr(settings, "API_MAX_CONCURRENT_STREAMS", 2))


def _check_session_token(request: QueryRequest) -> None:
    """若请求携带 session_id，则要求同时提供并验证 session_token。

    - session_id 为 None：匿名会话，无需鉴权。
    - session_id 已提供但 session_token 缺失：返回 401。
    - session_id 与 session_token 不匹配：返回 403。
    """
    if not request.session_id:
        return
    if not request.session_token:
        raise HTTPException(
            status_code=401,
            detail="提供 session_id 时必须同时携带 session_token（请先调用 POST /api/v1/sessions 创建会话）",
        )
    if not verify_session_token(request.session_id, request.session_token):
        raise HTTPException(status_code=403, detail="session_token 无效或与 session_id 不匹配")


@asynccontextmanager
async def _limited(semaphore: asyncio.Semaphore, *, purpose: str):
    """并发限制：超时则快速返回429，避免无限排队。"""
    timeout_sec = float(getattr(settings, "API_CONCURRENCY_ACQUIRE_TIMEOUT_SEC", 0.01))
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=timeout_sec)
    except TimeoutError:
        raise HTTPException(status_code=429, detail=f"并发过高，请稍后再试（{purpose}）")
    try:
        yield
    finally:
        semaphore.release()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    checks = {}
    overall_status = "healthy"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["db"] = HealthCheckItem(status="ok", detail="SELECT 1 成功")
    except Exception as exc:
        checks["db"] = HealthCheckItem(status="error", detail=str(exc))
        overall_status = "unhealthy"

    try:
        with engine.connect() as connection:
            has_vector = connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar()
        if has_vector:
            checks["pgvector"] = HealthCheckItem(status="ok", detail="pgvector 扩展已安装")
        else:
            checks["pgvector"] = HealthCheckItem(status="warn", detail="pgvector 扩展未安装或未启用")
    except Exception as exc:
        checks["pgvector"] = HealthCheckItem(status="warn", detail=f"检查失败: {exc}")

    try:
        ollama_base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        with urlopen(f"{ollama_base_url}/api/tags", timeout=3) as response:
            if response.status == 200:
                checks["ollama"] = HealthCheckItem(status="ok", detail="Ollama 可连通")
            else:
                checks["ollama"] = HealthCheckItem(status="warn", detail=f"Ollama 响应状态码: {response.status}")
    except URLError as exc:
        checks["ollama"] = HealthCheckItem(status="warn", detail=f"Ollama 不可达: {exc}")
    except Exception as exc:
        checks["ollama"] = HealthCheckItem(status="warn", detail=f"Ollama 检查失败: {exc}")

    return HealthResponse(status=overall_status, version="2.0.0-Agent", checks=checks)

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, http_request: Request):
    """标准问答"""
    _check_session_token(request)
    async with _limited(_QUERY_SEMAPHORE, purpose="query"):
        started = time.perf_counter()
        request_id = getattr(http_request.state, "request_id", "unknown")
        try:
            logger.info(
                "request_id={} session_id={} top_k={} category={} type=query start question={}",
                request_id,
                request.session_id or "default",
                request.k,
                request.category or "all",
                request.question[:50],
            )
            call = partial(
                medical_agent.query,
                question=request.question,
                thread_id=request.session_id or "default",
                k=request.k,
                category=request.category,
            )
            result = await anyio.to_thread.run_sync(call)
            debug_info = result.get("debug_info") or {}
            logger.info(
                "request_id={} session_id={} type=query done duration_ms={} retrieval_count={} top_score={} fallback_reason={}",
                request_id,
                request.session_id or "default",
                int((time.perf_counter() - started) * 1000),
                debug_info.get("retrieval_count", 0),
                debug_info.get("best_score"),
                debug_info.get("fallback_reason"),
            )
            result["request_id"] = request_id
            return QueryResponse(**result)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "request_id={} session_id={} type=query failed duration_ms={} error={}",
                request_id,
                request.session_id or "default",
                int((time.perf_counter() - started) * 1000),
                e,
            )
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/query-rag", response_model=QueryResponse)
async def query_rag(request: QueryRequest, http_request: Request):
    """RAG标准问答"""
    _check_session_token(request)
    async with _limited(_QUERY_SEMAPHORE, purpose="query-rag"):
        started = time.perf_counter()
        request_id = getattr(http_request.state, "request_id", "unknown")
        try:
            logger.info(
                "request_id={} session_id={} top_k={} category={} type=query-rag start question={}",
                request_id,
                request.session_id or "default",
                request.k,
                request.category or "all",
                request.question[:50],
            )
            call = partial(
                medical_agent.rag_chain.query,
                question=request.question,
                session_id=request.session_id or "default",
                k=request.k,
                filter_dict=medical_agent.rag_chain.build_filter_dict(request.category),
            )
            result = await anyio.to_thread.run_sync(call)
            debug_info = result.get("debug_info") or {}
            logger.info(
                "request_id={} session_id={} type=query-rag done duration_ms={} retrieval_count={} top_score={} fallback_reason={}",
                request_id,
                request.session_id or "default",
                int((time.perf_counter() - started) * 1000),
                debug_info.get("retrieval_count", 0),
                debug_info.get("best_score"),
                debug_info.get("fallback_reason"),
            )
            result["request_id"] = request_id
            return QueryResponse(**result)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "request_id={} session_id={} type=query-rag failed duration_ms={} error={}",
                request_id,
                request.session_id or "default",
                int((time.perf_counter() - started) * 1000),
                e,
            )
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/query-stream")
async def query_stream(request: QueryRequest, http_request: Request):
    """流式问答"""
    _check_session_token(request)
    request_id = getattr(http_request.state, "request_id", "unknown")

    async def generate():
        async with _limited(_STREAM_SEMAPHORE, purpose="query-stream"):
            try:
                # 注意：medical_agent.stream_query 是同步生成器；这里保持兼容，优先做并发保护。
                for event in medical_agent.stream_query(
                    question=request.question,
                    thread_id=request.session_id or "default",
                    k=request.k,
                    category=request.category,
                ):
                    if isinstance(event, dict) and event.get("type") == "end":
                        event = {**event, "request_id": request_id}
                    yield format_agent_event(event)
            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.post("/query-stream-rag")
async def query_stream_rag(request: QueryRequest, http_request: Request):
    """RAG流式问答"""
    _check_session_token(request)
    request_id = getattr(http_request.state, "request_id", "unknown")

    async def generate():
        async with _limited(_STREAM_SEMAPHORE, purpose="query-stream-rag"):
            try:
                async for event in medical_agent.rag_chain.stream_query(
                    question=request.question,
                    session_id=request.session_id or "default",
                    k=request.k,
                    filter_dict=medical_agent.rag_chain.build_filter_dict(request.category),
                ):
                    if isinstance(event, dict) and event.get("type") == "end":
                        event = {**event, "request_id": request_id}
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
