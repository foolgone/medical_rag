"""
对话摘要记忆管理
"""
from typing import Dict, List, Optional

from loguru import logger

from database.connection import get_db_session
from database.models import ConversationHistory, ConversationSummary


class MemorySummaryManager:
    """负责判断、生成和保存阶段摘要。"""

    def __init__(self, summary_trigger_rounds: int = 4):
        self.summary_trigger_rounds = summary_trigger_rounds

    def should_summarize(self, session_id: str) -> bool:
        """判断当前会话是否需要生成新的阶段摘要。"""
        unsummarized = self.load_unsummarized_history(session_id)
        return len(unsummarized) >= self.summary_trigger_rounds

    def load_unsummarized_history(
        self,
        session_id: str,
        max_rounds: int = 8
    ) -> List[Dict]:
        """获取尚未被摘要覆盖的最近若干轮历史。"""
        try:
            with get_db_session() as db:
                latest_summary = db.query(ConversationSummary) \
                    .filter(ConversationSummary.session_id == session_id) \
                    .order_by(ConversationSummary.end_history_id.desc()) \
                    .first()

                query = db.query(ConversationHistory) \
                    .filter(ConversationHistory.session_id == session_id)

                if latest_summary:
                    query = query.filter(ConversationHistory.id > latest_summary.end_history_id)

                records = query.order_by(ConversationHistory.id.asc()).limit(max_rounds).all()
                return [
                    {
                        "id": record.id,
                        "question": record.question,
                        "answer": record.answer,
                    }
                    for record in records
                ]
        except Exception as e:
            logger.error(f"加载未摘要历史失败: {e}")
            return []

    def generate_summary(self, history_records: List[Dict]) -> str:
        """生成简洁的阶段摘要。"""
        if not history_records:
            return ""

        first_question = history_records[0]["question"]
        latest_question = history_records[-1]["question"]
        symptoms = []
        diseases = []
        medications = []
        allergies = []

        combined_text = " ".join(
            f"{record['question']} {record['answer']}" for record in history_records
        )

        for keyword in ["发热", "头痛", "咳嗽", "胸闷", "腹痛", "乏力", "头晕"]:
            if keyword in combined_text and keyword not in symptoms:
                symptoms.append(keyword)

        for keyword in ["高血压", "糖尿病", "哮喘", "冠心病"]:
            if keyword in combined_text and keyword not in diseases:
                diseases.append(keyword)

        for keyword in ["青霉素", "头孢", "阿司匹林"]:
            if keyword in combined_text and keyword not in allergies:
                allergies.append(keyword)

        for keyword in ["二甲双胍", "胰岛素", "氨氯地平", "降压药"]:
            if keyword in combined_text and keyword not in medications:
                medications.append(keyword)

        lines = [
            f"本阶段共 {len(history_records)} 轮对话。",
            f"最早问题：{first_question[:60]}",
            f"当前关注：{latest_question[:60]}",
        ]

        if symptoms:
            lines.append("主要症状：" + "、".join(symptoms))
        if diseases:
            lines.append("既往病史：" + "、".join(diseases))
        if allergies:
            lines.append("过敏提示：" + "、".join(allergies))
        if medications:
            lines.append("相关用药：" + "、".join(medications))

        return "\n".join(lines[:6])

    def save_summary(
        self,
        session_id: str,
        summary_text: str,
        start_history_id: int,
        end_history_id: int,
        message_count: int
    ) -> bool:
        """保存阶段摘要。"""
        if not summary_text:
            return False

        try:
            with get_db_session() as db:
                summary = ConversationSummary(
                    session_id=session_id,
                    start_history_id=start_history_id,
                    end_history_id=end_history_id,
                    summary_text=summary_text,
                    message_count=message_count,
                )
                db.add(summary)
            return True
        except Exception as e:
            logger.error(f"保存对话摘要失败: {e}")
            return False

    def get_latest_summary(self, session_id: str) -> Optional[Dict]:
        """获取最近一条阶段摘要。"""
        try:
            with get_db_session() as db:
                summary = db.query(ConversationSummary) \
                    .filter(ConversationSummary.session_id == session_id) \
                    .order_by(ConversationSummary.created_at.desc()) \
                    .first()

                if not summary:
                    return None

                return {
                    "id": summary.id,
                    "session_id": summary.session_id,
                    "summary_text": summary.summary_text,
                    "start_history_id": summary.start_history_id,
                    "end_history_id": summary.end_history_id,
                    "message_count": summary.message_count,
                    "created_at": summary.created_at.isoformat(),
                }
        except Exception as e:
            logger.error(f"获取对话摘要失败: {e}")
            return None

    def refresh_summary_if_needed(self, session_id: str) -> bool:
        """在达到阈值时自动生成新的阶段摘要。"""
        history_records = self.load_unsummarized_history(session_id)
        if len(history_records) < self.summary_trigger_rounds:
            return False

        summary_text = self.generate_summary(history_records)
        return self.save_summary(
            session_id=session_id,
            summary_text=summary_text,
            start_history_id=history_records[0]["id"],
            end_history_id=history_records[-1]["id"],
            message_count=len(history_records),
        )
