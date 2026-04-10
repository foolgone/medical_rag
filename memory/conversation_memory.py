"""
对话记忆管理模块
提供短期记忆（窗口记忆）和长期记忆（向量检索记忆）
支持 Agent 系统的上下文管理和个性化记忆
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import desc
from loguru import logger

from database.connection import get_db_session
from database.models import ConversationHistory


class ConversationMemory:
    """
    对话记忆管理器

    功能：
    1. 短期记忆：保留最近 N 轮对话
    2. 长期记忆：从数据库检索历史相关对话
    3. 记忆提取：从对话中提取关键信息
    4. 会话管理：创建、查询、删除会话
    """

    def __init__(self, window_size: int = 5):
        """
        初始化记忆管理器

        Args:
            window_size: 短期记忆窗口大小（保留最近几轮对话）
        """
        self.window_size = window_size
        logger.info(f"对话记忆管理器初始化完成，窗口大小: {window_size}")

    # ==================== 短期记忆 ====================

    def get_short_term_memory(self, session_id: str) -> List[Dict]:
        """
        获取短期记忆（最近 N 轮对话）

        Args:
            session_id: 会话ID

        Returns:
            对话历史列表，按时间正序排列
        """
        try:
            with get_db_session() as db:
                history = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .order_by(desc(ConversationHistory.created_at)) \
                    .limit(self.window_size) \
                    .all()

                # 提取数据并反转为正序
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
        """
        格式化短期记忆为文本（用于拼接到 prompt）

        Args:
            session_id: 会话ID

        Returns:
            格式化的对话历史文本
        """
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
        """
        获取长期记忆（所有历史对话）

        Args:
            session_id: 会话ID
            limit: 返回的最大记录数

        Returns:
            完整对话历史列表
        """
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
                        "question": record.question,
                        "answer": record.answer,
                        "context": record.context,
                        "created_at": record.created_at.isoformat()
                    })

                logger.debug(f"获取长期记忆，session_id: {session_id}, 记录数: {len(messages)}")
                return messages
        except Exception as e:
            logger.error(f"获取长期记忆失败: {e}")
            return []

    def search_relevant_memory(self, query: str, session_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """
        搜索相关的历史记忆（基于关键词匹配）

        TODO: 未来可升级为向量相似度检索

        Args:
            query: 查询文本
            session_id: 可选的会话ID过滤
            limit: 返回结果数量

        Returns:
            相关的历史对话列表
        """
        try:
            with get_db_session() as db:
                query_obj = db.query(ConversationHistory)

                # 如果指定了会话ID，只在该会话中搜索
                if session_id:
                    query_obj = query_obj.filter(ConversationHistory.session_id == session_id)

                # 简单关键词匹配（实际应使用向量检索）
                # 这里使用 LIKE 进行模糊搜索
                history = query_obj \
                    .filter(
                    (ConversationHistory.question.ilike(f"%{query}%")) |
                    (ConversationHistory.answer.ilike(f"%{query}%"))
                ) \
                    .order_by(desc(ConversationHistory.created_at)) \
                    .limit(limit) \
                    .all()

                results = []
                for record in history:
                    results.append({
                        "question": record.question,
                        "answer": record.answer,
                        "relevance": "keyword_match",
                        "created_at": record.created_at.isoformat()
                    })

                logger.debug(f"搜索相关记忆，query: {query[:30]}..., 结果数: {len(results)}")
                return results
        except Exception as e:
            logger.error(f"搜索相关记忆失败: {e}")
            return []

    # ==================== 记忆保存 ====================

    def save_conversation(self, session_id: str, question: str, answer: str, context: str = "") -> bool:
        """
        保存一轮对话到数据库

        Args:
            session_id: 会话ID
            question: 用户问题
            answer: AI回答
            context: 检索的上下文（可选）

        Returns:
            是否保存成功
        """
        try:
            with get_db_session() as db:
                conversation = ConversationHistory(
                    session_id=session_id,
                    question=question,
                    answer=answer,
                    context=context
                )
                db.add(conversation)

            logger.debug(f"对话已保存，session_id: {session_id}")
            return True
        except Exception as e:
            logger.error(f"保存对话失败: {e}")
            return False

    def save_agent_interaction(self, session_id: str, question: str,
                               answer: str, tools_used: List[str] = None,
                               reasoning_steps: List[str] = None) -> bool:
        """
        保存 Agent 交互记录（包含工具使用和推理过程）

        Args:
            session_id: 会话ID
            question: 用户问题
            answer: AI回答
            tools_used: 使用的工具列表
            reasoning_steps: 推理步骤列表

        Returns:
            是否保存成功
        """
        try:
            # 构建增强的上下文字符串
            context_parts = []

            if tools_used:
                context_parts.append(f"使用的工具: {', '.join(tools_used)}")

            if reasoning_steps:
                context_parts.append("推理过程:")
                for i, step in enumerate(reasoning_steps, 1):
                    context_parts.append(f"  {i}. {step}")

            context = "\n".join(context_parts) if context_parts else ""

            return self.save_conversation(session_id, question, answer, context)
        except Exception as e:
            logger.error(f"保存 Agent 交互失败: {e}")
            return False

    # ==================== 会话管理 ====================

    def create_session(self) -> str:
        """
        创建新会话

        Returns:
            会话ID
        """
        import uuid
        session_id = str(uuid.uuid4())
        logger.info(f"创建新会话: {session_id}")
        return session_id

    def get_session_stats(self, session_id: str) -> Dict:
        """
        获取会话统计信息

        Args:
            session_id: 会话ID

        Returns:
            统计数据字典
        """
        try:
            with get_db_session() as db:
                total_count = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .count()

                first_record = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .order_by(ConversationHistory.created_at) \
                    .first()

                last_record = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .order_by(desc(ConversationHistory.created_at)) \
                    .first()

                stats = {
                    "session_id": session_id,
                    "total_interactions": total_count,
                    "first_interaction": first_record.created_at.isoformat() if first_record else None,
                    "last_interaction": last_record.created_at.isoformat() if last_record else None,
                }

                return stats
        except Exception as e:
            logger.error(f"获取会话统计失败: {e}")
            return {"session_id": session_id, "error": str(e)}

    def delete_session(self, session_id: str) -> bool:
        """
        删除整个会话的所有记录

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        try:
            with get_db_session() as db:
                deleted_count = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id) \
                    .delete()

                logger.info(f"删除会话 {session_id}，共 {deleted_count} 条记录")
                return True
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False

    def clear_old_sessions(self, days: int = 30) -> int:
        """
        清理过期会话

        Args:
            days: 保留天数，超过此天数的会话将被删除

        Returns:
            删除的记录数
        """
        try:
            from sqlalchemy import text

            with get_db_session() as db:
                result = db.execute(text("""
                    DELETE FROM conversation_history 
                    WHERE created_at < NOW() - INTERVAL ':days days'
                """), {"days": days})

                deleted_count = result.rowcount
                logger.info(f"清理过期会话，删除 {deleted_count} 条记录")
                return deleted_count
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0

    # ==================== 记忆提取 ====================

    def extract_key_info(self, session_id: str) -> Dict:
        """
        从会话中提取关键信息（患者档案）

        TODO: 可使用 LLM 自动提取结构化信息

        Args:
            session_id: 会话ID

        Returns:
            提取的关键信息字典
        """
        try:
            history = self.get_long_term_memory(session_id, limit=50)

            key_info = {
                "session_id": session_id,
                "total_interactions": len(history),
                "mentioned_symptoms": [],
                "mentioned_conditions": [],
                "mentioned_medications": [],
                "patient_profile": {}
            }

            # 简单关键词提取（实际应使用 LLM 或 NLP）
            symptom_keywords = ["头痛", "发热", "咳嗽", "腹痛", "恶心", "呕吐", "乏力"]
            condition_keywords = ["糖尿病", "高血压", "心脏病", "哮喘", "过敏"]
            medication_keywords = ["阿司匹林", "布洛芬", "胰岛素", "降压药"]

            for record in history:
                text = f"{record['question']} {record['answer']}"

                for symptom in symptom_keywords:
                    if symptom in text and symptom not in key_info["mentioned_symptoms"]:
                        key_info["mentioned_symptoms"].append(symptom)

                for condition in condition_keywords:
                    if condition in text and condition not in key_info["mentioned_conditions"]:
                        key_info["mentioned_conditions"].append(condition)

                for med in medication_keywords:
                    if med in text and med not in key_info["mentioned_medications"]:
                        key_info["mentioned_medications"].append(med)

            logger.info(f"提取关键信息完成，session_id: {session_id}")
            return key_info
        except Exception as e:
            logger.error(f"提取关键信息失败: {e}")
            return {"session_id": session_id, "error": str(e)}


# ==================== LangGraph Checkpointer 集成 ====================

class LangGraphMemorySaver:
    """
    LangGraph 记忆保存器
    将 LangGraph 的检查点保存到 PostgreSQL
    """

    def __init__(self):
        self.memory = ConversationMemory()
        logger.info("LangGraph 记忆保存器初始化完成")

    def put(self, config: dict, checkpoint: dict, metadata: dict) -> None:
        """
        保存检查点

        Args:
            config: 配置字典（包含 thread_id）
            checkpoint: 检查点数据
            metadata: 元数据
        """
        try:
            thread_id = config.get("configurable", {}).get("thread_id", "default")
            # 这里可以序列化 checkpoint 并保存到数据库
            logger.debug(f"保存检查点，thread_id: {thread_id}")
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")

    def get(self, config: dict) -> Optional[dict]:
        """
        获取检查点

        Args:
            config: 配置字典

        Returns:
            检查点数据
        """
        try:
            thread_id = config.get("configurable", {}).get("thread_id", "default")
            logger.debug(f"获取检查点，thread_id: {thread_id}")
            return None  # TODO: 实现实际读取逻辑
        except Exception as e:
            logger.error(f"获取检查点失败: {e}")
            return None


# ==================== 全局实例 ====================

# 创建默认的记忆管理器实例
default_memory = ConversationMemory(window_size=5)
