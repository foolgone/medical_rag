"""会话生命周期管理路由

提供会话的创建、查询、删除等管理接口。
每个会话在创建时颁发一次性令牌（session_token），后续操作均需携带该令牌以验证所有权。
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from loguru import logger

from api.schemas import CreateSessionResponse, SessionStatsResponse
from database.connection import get_db_session
from database.models import SessionToken
from memory.conversation_memory import default_memory

router = APIRouter(prefix="/sessions", tags=["会话管理"])


# ──────────────────────────────────────────────────────────────
# 内部工具函数
# ──────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    """返回令牌的 SHA-256 十六进制摘要，用于数据库存储。"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_session_token(session_id: str, session_token: str) -> bool:
    """验证 session_token 是否与 session_id 的存储哈希匹配。

    使用 `hmac.compare_digest` 防止时序攻击。
    验证成功时同步更新 `last_used_at`；`get_db_session` 上下文管理器会在退出时自动提交。
    """
    try:
        expected_hash = _hash_token(session_token)
        with get_db_session() as db:
            record = db.query(SessionToken).filter(
                SessionToken.session_id == session_id
            ).first()
            if not record:
                return False
            matched = hmac.compare_digest(record.token_hash, expected_hash)
            if matched:
                # get_db_session 退出时会 commit，此处赋值即可持久化
                record.last_used_at = datetime.now(timezone.utc)
            return matched
    except Exception as e:
        logger.error(f"验证 session_token 失败: {e}")
        return False


def _require_valid_token(session_id: str, x_session_token: Optional[str]) -> None:
    """若令牌缺失或不匹配则抛出 HTTP 异常。"""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="缺少 X-Session-Token 请求头")
    if not verify_session_token(session_id, x_session_token):
        raise HTTPException(status_code=403, detail="session_token 无效或与 session_id 不匹配")


# ──────────────────────────────────────────────────────────────
# 路由
# ──────────────────────────────────────────────────────────────

@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session():
    """创建新会话。

    返回 `session_id` 和 `session_token`。令牌**仅在此处返回一次**，请客户端妥善保存。
    后续对该会话的所有查询及管理操作均需在请求体（查询接口）或
    `X-Session-Token` 头（管理接口）中携带此令牌。
    """
    session_id = default_memory.create_session()
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    try:
        with get_db_session() as db:
            db.add(SessionToken(session_id=session_id, token_hash=token_hash))
        logger.info(f"会话已创建: {session_id}")
        return CreateSessionResponse(session_id=session_id, session_token=token)
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionStatsResponse)
async def get_session(
    session_id: str,
    x_session_token: Optional[str] = Header(None, description="会话令牌"),
):
    """获取会话统计信息（需要 X-Session-Token 头）。"""
    _require_valid_token(session_id, x_session_token)
    stats = default_memory.get_session_stats(session_id)
    if "error" in stats:
        raise HTTPException(status_code=500, detail=stats["error"])
    return SessionStatsResponse(**stats)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    x_session_token: Optional[str] = Header(None, description="会话令牌"),
):
    """删除会话及其所有历史记录（需要 X-Session-Token 头）。"""
    _require_valid_token(session_id, x_session_token)
    try:
        with get_db_session() as db:
            db.query(SessionToken).filter(SessionToken.session_id == session_id).delete()
        default_memory.delete_session(session_id)
        logger.info(f"会话已删除: {session_id}")
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
