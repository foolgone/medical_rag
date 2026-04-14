"""
对话记忆管理模块
提供短期记忆、事实记忆和摘要记忆的统一读写能力
"""
import json
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import desc

from database.connection import get_db_session
from database.models import ConversationHistory, ConversationSummary, PatientFactMemory
from memory.memory_extractor import MemoryExtractor
from memory.memory_summary import MemorySummaryManager


class ConversationMemory:
    """
    对话记忆管理器

    功能：
    1. 短期记忆：保留最近 N 轮原始对话
    2. 事实记忆：结构化保存用户背景信息
    3. 摘要记忆：对长会话阶段进行压缩
    4. 会话管理：创建、查询、删除会话
    """

    def __init__(self, window_size: int = 5, summary_trigger_rounds: int = 4):
        self.window_size = window_size
        self.extractor = MemoryExtractor()
        self.summary_manager = MemorySummaryManager(summary_trigger_rounds=summary_trigger_rounds)
        logger.info(
            f"对话记忆管理器初始化完成，窗口大小: {window_size}, 摘要阈值: {summary_trigger_rounds}"
        )

    @staticmethod
    def _safe_json_loads(value: Optional[str], default: Any):
        """安全解析JSON文本"""
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        return (value or "").strip()

    # ==================== 短期记忆 ====================

    def get_short_term_memory(self, session_id: str) -> List[Dict]:
        """获取最近 N 轮原始对话，按时间正序排列。"""
        try:
            with get_db_session() as db:
                history = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .order_by(desc(ConversationHistory.created_at)) \
                    .limit(self.window_size) \
                    .all()

                messages = []
                for record in reversed(history):
                    messages.append({
                        "role": "user",
                        "content": record.question
                    })
                    messages.append({
                        "role": "assistant",
                        "content": record.answer
                    })

                logger.debug(f"获取短期记忆，session_id: {session_id}, 消息数: {len(messages)}")
                return messages
        except Exception as e:
            logger.error(f"获取短期记忆失败: {e}")
            return []

    def format_short_term_memory(self, session_id: str) -> str:
        """格式化短期记忆为文本。"""
        messages = self.get_short_term_memory(session_id)
        if not messages:
            return ""

        formatted = "【历史对话】\n"
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            formatted += f"{role}: {msg['content']}\n"
        return formatted

    # ==================== 长期记忆 ====================

    def get_long_term_memory(self, session_id: str, limit: int = 10) -> List[Dict]:
        """获取完整历史对话列表。"""
        try:
            with get_db_session() as db:
                history = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .order_by(ConversationHistory.created_at) \
                    .limit(limit) \
                    .all()

                messages = []
                for record in history:
                    messages.append({
                        "id": record.id,
                        "question": record.question,
                        "answer": record.answer,
                        "context": record.context,
                        "tools_used": self._safe_json_loads(record.tools_used, []),
                        "record_type": record.record_type,
                        "memory_metadata": self._safe_json_loads(record.memory_metadata, {}),
                        "created_at": record.created_at.isoformat()
                    })

                logger.debug(f"获取长期记忆，session_id: {session_id}, 记录数: {len(messages)}")
                return messages
        except Exception as e:
            logger.error(f"获取长期记忆失败: {e}")
            return []

    def search_relevant_memory(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """基于关键词搜索相关历史记忆。"""
        try:
            with get_db_session() as db:
                query_obj = db.query(ConversationHistory)

                if session_id:
                    query_obj = query_obj.filter(ConversationHistory.session_id == session_id)

                history = query_obj.filter(
                    (ConversationHistory.question.ilike(f"%{query}%")) |
                    (ConversationHistory.answer.ilike(f"%{query}%"))
                ).order_by(desc(ConversationHistory.created_at)).limit(limit).all()

                results = []
                for record in history:
                    results.append({
                        "question": record.question,
                        "answer": record.answer,
                        "relevance": "keyword_match",
                        "created_at": record.created_at.isoformat()
                    })
                return results
        except Exception as e:
            logger.error(f"搜索相关记忆失败: {e}")
            return []

    # ==================== 事实记忆 ====================

    def get_fact_memory(self, session_id: str) -> List[Dict]:
        """获取当前会话有效的事实记忆。"""
        try:
            with get_db_session() as db:
                rows = db.query(PatientFactMemory) \
                    .filter(PatientFactMemory.session_id == session_id) \
                    .filter(PatientFactMemory.status == "active") \
                    .order_by(PatientFactMemory.updated_at.desc()) \
                    .all()

                return [
                    {
                        "fact_type": row.fact_type,
                        "fact_key": row.fact_key,
                        "fact_value": row.fact_value,
                        "confidence": row.confidence,
                        "source": row.source,
                        "status": row.status,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取事实记忆失败: {e}")
            return []

    def upsert_fact_memory(self, session_id: str, facts: List[Dict]) -> bool:
        """写入或更新事实记忆，发生冲突时保留最新 active 版本。"""
        if not facts:
            return True

        try:
            with get_db_session() as db:
                for fact in facts:
                    existing = db.query(PatientFactMemory) \
                        .filter(PatientFactMemory.session_id == session_id) \
                        .filter(PatientFactMemory.fact_type == fact["fact_type"]) \
                        .filter(PatientFactMemory.fact_key == fact["fact_key"]) \
                        .filter(PatientFactMemory.status == "active") \
                        .order_by(PatientFactMemory.updated_at.desc()) \
                        .first()

                    if existing and existing.fact_value == fact["fact_value"]:
                        existing.confidence = max(existing.confidence, fact.get("confidence", 0.8))
                        existing.source = fact.get("source", existing.source)
                        continue

                    if existing:
                        existing.status = "superseded"

                    db.add(
                        PatientFactMemory(
                            session_id=session_id,
                            fact_type=fact["fact_type"],
                            fact_key=fact["fact_key"],
                            fact_value=fact["fact_value"],
                            confidence=fact.get("confidence", 0.8),
                            source=fact.get("source", "user_explicit"),
                            status=fact.get("status", "active"),
                        )
                    )
            return True
        except Exception as e:
            logger.error(f"写入事实记忆失败: {e}")
            return False

    @staticmethod
    def format_fact_memory(facts: List[Dict]) -> str:
        """将事实记忆整理成可注入 prompt 的文本。"""
        if not facts:
            return ""

        type_labels = {
            "profile": "基础信息",
            "disease_history": "既往病史",
            "allergy": "过敏信息",
            "medication": "用药信息",
            "persistent_symptom": "持续症状",
        }
        lines = []
        for fact in facts:
            label = type_labels.get(fact["fact_type"], fact["fact_type"])
            lines.append(f"- {label}: {fact['fact_value']}")
        return "\n".join(lines)

    # ==================== 摘要记忆 ====================

    def get_latest_summary(self, session_id: str) -> Optional[Dict]:
        """获取最近一条摘要记忆。"""
        return self.summary_manager.get_latest_summary(session_id)

    def refresh_summary_if_needed(self, session_id: str) -> bool:
        """按阈值判断是否生成新摘要。"""
        return self.summary_manager.refresh_summary_if_needed(session_id)

    # ==================== 记忆组合 ====================

    def build_memory_bundle(self, session_id: str, query: Optional[str] = None) -> Dict[str, Any]:
        """构建当前轮需要注入的分层记忆包。"""
        short_term_messages = self.get_short_term_memory(session_id) if session_id else []
        fact_memory = self.get_fact_memory(session_id) if session_id else []
        latest_summary = self.get_latest_summary(session_id) if session_id else None

        return {
            "short_term_messages": short_term_messages,
            "fact_memory": fact_memory,
            "summary_memory": latest_summary["summary_text"] if latest_summary else "",
            "query": query,
            "debug_info": {
                "memory_message_count": len(short_term_messages),
                "fact_count": len(fact_memory),
                "summary_applied": bool(latest_summary and latest_summary.get("summary_text")),
            }
        }

    # ==================== 记忆保存 ====================

    def save_conversation(
        self,
        session_id: str,
        question: str,
        answer: str,
        context: str = "",
        tools_used: Optional[List[str]] = None,
        record_type: str = "chat",
        memory_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """保存一轮对话到数据库。"""
        try:
            with get_db_session() as db:
                conversation = ConversationHistory(
                    session_id=session_id,
                    question=question,
                    answer=answer,
                    context=context,
                    tools_used=json.dumps(tools_used or [], ensure_ascii=False),
                    record_type=record_type,
                    memory_metadata=json.dumps(memory_metadata or {}, ensure_ascii=False)
                )
                db.add(conversation)
            logger.debug(f"对话已保存，session_id: {session_id}")
            return True
        except Exception as e:
            logger.error(f"保存对话失败: {e}")
            return False

    def save_agent_interaction(
        self,
        session_id: str,
        question: str,
        answer: str,
        tools_used: List[str] = None,
        reasoning_steps: List[str] = None,
        memory_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """保存 Agent 交互，并同步刷新事实记忆与摘要记忆。"""
        try:
            context_parts = []
            if tools_used:
                context_parts.append(f"使用的工具: {', '.join(tools_used)}")
            if reasoning_steps:
                context_parts.append("推理过程:")
                for i, step in enumerate(reasoning_steps, 1):
                    context_parts.append(f"  {i}. {step}")

            context = "\n".join(context_parts) if context_parts else ""
            saved = self.save_conversation(
                session_id=session_id,
                question=question,
                answer=answer,
                context=context,
                tools_used=tools_used,
                record_type="agent",
                memory_metadata=memory_metadata
            )

            if not saved:
                return False

            facts = self.extractor.extract_facts(question=question, answer=answer, context=context)
            self.upsert_fact_memory(session_id, facts)
            self.refresh_summary_if_needed(session_id)
            return True
        except Exception as e:
            logger.error(f"保存 Agent 交互失败: {e}")
            return False

    # ==================== 会话管理 ====================

    def create_session(self) -> str:
        """创建新会话。"""
        import uuid
        session_id = str(uuid.uuid4())
        logger.info(f"创建新会话: {session_id}")
        return session_id

    def get_session_stats(self, session_id: str) -> Dict:
        """获取会话统计信息。"""
        try:
            with get_db_session() as db:
                total_count = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .count()

                fact_count = db.query(PatientFactMemory) \
                    .filter(PatientFactMemory.session_id == session_id) \
                    .filter(PatientFactMemory.status == "active") \
                    .count()

                summary_count = db.query(ConversationSummary) \
                    .filter(ConversationSummary.session_id == session_id) \
                    .count()

                first_record = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .order_by(ConversationHistory.created_at) \
                    .first()

                last_record = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .order_by(desc(ConversationHistory.created_at)) \
                    .first()

                return {
                    "session_id": session_id,
                    "total_interactions": total_count,
                    "fact_count": fact_count,
                    "summary_count": summary_count,
                    "first_interaction": first_record.created_at.isoformat() if first_record else None,
                    "last_interaction": last_record.created_at.isoformat() if last_record else None,
                }
        except Exception as e:
            logger.error(f"获取会话统计失败: {e}")
            return {"session_id": session_id, "error": str(e)}

    def delete_session(self, session_id: str) -> bool:
        """删除整个会话的所有记录。"""
        try:
            with get_db_session() as db:
                history_count = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .delete()

                fact_count = db.query(PatientFactMemory) \
                    .filter(PatientFactMemory.session_id == session_id) \
                    .delete()

                summary_count = db.query(ConversationSummary) \
                    .filter(ConversationSummary.session_id == session_id) \
                    .delete()

                logger.info(
                    f"删除会话 {session_id}，历史 {history_count} 条，事实 {fact_count} 条，摘要 {summary_count} 条"
                )
                return True
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False

    def clear_old_sessions(self, days: int = 30) -> int:
        """清理过期会话。"""
        try:
            from sqlalchemy import text

            with get_db_session() as db:
                result = db.execute(text(f"""
                    DELETE FROM conversation_history
                    WHERE created_at < NOW() - INTERVAL '{days} days'
                """))
                deleted_count = result.rowcount
                logger.info(f"清理过期会话，删除 {deleted_count} 条记录")
                return deleted_count
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0

    # ==================== 记忆提取 ====================

    def extract_key_info(self, session_id: str) -> Dict:
        """从事实记忆中提取患者关键信息。"""
        try:
            fact_memory = self.get_fact_memory(session_id)
            profile = {}
            symptoms = []
            diseases = []
            medications = []
            allergies = []

            for fact in fact_memory:
                if fact["fact_type"] == "profile":
                    profile[fact["fact_key"]] = fact["fact_value"]
                elif fact["fact_type"] == "persistent_symptom":
                    symptoms.append(fact["fact_value"])
                elif fact["fact_type"] == "disease_history":
                    diseases.append(fact["fact_value"])
                elif fact["fact_type"] == "medication":
                    medications.append(fact["fact_value"])
                elif fact["fact_type"] == "allergy":
                    allergies.append(fact["fact_value"])

            return {
                "session_id": session_id,
                "total_interactions": len(self.get_long_term_memory(session_id, limit=50)),
                "mentioned_symptoms": symptoms,
                "mentioned_conditions": diseases,
                "mentioned_medications": medications,
                "mentioned_allergies": allergies,
                "patient_profile": profile
            }
        except Exception as e:
            logger.error(f"提取关键信息失败: {e}")
            return {"session_id": session_id, "error": str(e)}


class LangGraphMemorySaver:
    """
    LangGraph 记忆保存器
    将 LangGraph 的检查点保存到 PostgreSQL
    """

    def __init__(self):
        self.memory = ConversationMemory()
        logger.info("LangGraph 记忆保存器初始化完成")

    def put(self, config: dict, checkpoint: dict, metadata: dict) -> None:
        """保存检查点。"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id", "default")
            logger.debug(f"保存检查点，thread_id: {thread_id}")
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")

    def get(self, config: dict) -> Optional[dict]:
        """获取检查点。"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id", "default")
            logger.debug(f"获取检查点，thread_id: {thread_id}")
            return None
        except Exception as e:
            logger.error(f"获取检查点失败: {e}")
            return None


default_memory = ConversationMemory(window_size=5)
