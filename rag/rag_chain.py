"""
RAG链核心逻辑
整合检索和生成，提供完整的问答流程
"""
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional
from pathlib import Path
import threading
import time
from langchain_core.documents import Document
from rag.document_loader import MedicalDocumentLoader
from rag.md5_checker import MD5Checker
from rag.text_splitter import MedicalTextSplitter
from rag.vector_store import MedicalVectorStore, MedicalEmbeddings
from rag.retriever import MedicalRetriever
from llm.ollama_client import MedicalLLMClient
from database.connection import get_db_session
from database.models import ConversationHistory, KnowledgeBaseFile, KnowledgeBaseIngestJob
from sqlalchemy import func
from loguru import logger
import uuid
from config import settings


class MedicalRAGChain:
    """医疗RAG链"""
    
    def __init__(self):
        """初始化RAG链各组件"""
        logger.info("初始化医疗RAG链...")
        
        # 初始化组件
        self.document_loader = MedicalDocumentLoader()
        self.text_splitter = MedicalTextSplitter()
        self.embeddings = MedicalEmbeddings()
        self.vector_store = MedicalVectorStore(embeddings=self.embeddings)
        self.retriever = MedicalRetriever(vector_store=self.vector_store)
        self.llm_client = MedicalLLMClient()

        # 第9步MVP：stats 短TTL缓存
        self._stats_cache_lock = threading.Lock()
        self._stats_cache_value: Optional[Dict] = None
        self._stats_cache_expires_at: float = 0.0
        
        logger.info("医疗RAG链初始化完成")

    @staticmethod
    def build_filter_dict(category: Optional[str] = None) -> Optional[Dict[str, str]]:
        """构建检索过滤条件"""
        if not category or category == "all":
            return None
        return {"category": category}

    @staticmethod
    def serialize_sources(documents: List[Document]) -> List[Dict]:
        """序列化来源信息"""
        return [
            {
                "source": doc.metadata.get("source", "未知"),
                "category": doc.metadata.get("category", "未知"),
                "content": doc.page_content[:200],
                "score": doc.metadata.get("score"),
                "raw_score": doc.metadata.get("raw_score"),
                "keyword_score": doc.metadata.get("keyword_score"),
                "rerank_score": doc.metadata.get("rerank_score"),
                "page": doc.metadata.get("page"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "source_type": doc.metadata.get("source_type"),
                "updated_at": doc.metadata.get("updated_at"),
                "retrieval_methods": doc.metadata.get("retrieval_methods", []),
            }
            for doc in documents
        ]

    @staticmethod
    def build_low_confidence_notice(best_score: Optional[float]) -> str:
        """构建低置信检索提示。"""
        if best_score is None:
            return "注意：当前知识库命中不足，以下回答可能不完全对应你的问题，建议结合医生意见判断。"

        return (
            "注意：当前知识库命中不足，"
            f"本次检索最佳匹配分数约为 {best_score:.2f}，"
            "以下回答仅供参考，建议结合医生意见判断。"
        )
    
    def ingest_documents(self, data_dir: str = None, category: str = "general") -> int:
        """
        导入文档到知识库
        
        Args:
            data_dir: 文档目录
            category: 文档分类
            
        Returns:
            导入的文档数量
        """
        try:
            from rag.knowledge_base_update import KnowledgeBaseUpdateService

            logger.info(f"开始导入文档，目录: {data_dir or 'default'}")
            result = KnowledgeBaseUpdateService(self).incremental_update(data_dir=data_dir, category=category)
            logger.info(f"知识库导入完成: {result}")
            return int(result.get("ingested_count", 0))
        except Exception as e:
            logger.error(f"文档导入失败: {e}")
            raise

    def query(
        self,
        question: str,
        session_id: Optional[str] = None,
        k: int = None,
        filter_dict: Optional[dict] = None
    ) -> Dict:
        """
        回答问题

        Args:
            question: 用户问题
            session_id: 会话ID（用于保存历史）
            k: 检索文档数量
            filter_dict: 过滤条件

        Returns:
            包含回答和相关信息的字典
        """
        try:
            logger.info(f"处理问题: {question[:50]}...")

            # 检索相关文档
            retrieval = self.retriever.retrieve_with_diagnostics(question, k=k, filter_dict=filter_dict)
            docs = retrieval["documents"]
            low_confidence = retrieval["low_confidence"]
            best_score = retrieval["best_score"]

            if not docs:
                # 如果没有检索到文档，直接使用LLM聊天模式
                logger.info("未检索到相关文档，使用聊天模式")
                answer = self._chat_mode(question, session_id)
                context = ""
            else:
                # 格式化上下文
                context = self.retriever.format_context(docs)

                # 生成回答
                answer = self.llm_client.generate_with_context(question, context)
                if low_confidence:
                    answer = f"{answer}\n\n{self.build_low_confidence_notice(best_score)}"

            # 保存对话历史
            if session_id:
                self._save_conversation(session_id, question, answer, context)

            result = {
                "question": question,
                "answer": answer,
                "session_id": session_id,
                "sources": self.serialize_sources(docs),
                "tool_calls": [],
                "tool_calls_count": 0,
                "debug_info": {
                    "requested_k": k,
                    "applied_category": filter_dict.get("category") if filter_dict else None,
                    "retrieval_count": len(docs),
                    "used_chat_mode": not docs,
                    "low_confidence": low_confidence,
                    "best_score": best_score,
                    "fallback_reason": "no_retrieval" if not docs else ("low_confidence" if low_confidence else None),
                    "retrieval_strategy": retrieval.get("retrieval_strategy"),
                    "vector_result_count": retrieval.get("vector_result_count", 0),
                    "keyword_result_count": retrieval.get("keyword_result_count", 0),
                    "merged_result_count": retrieval.get("merged_result_count", 0),
                    "rewritten_query": retrieval.get("rewritten_query"),
                },
            }

            logger.info("问题回答完成")
            return result
        except Exception as e:
            logger.error(f"回答问题失败: {e}")
            raise

    async def stream_query(
        self,
        question: str,
        session_id: Optional[str] = None,
        k: int = None,
        filter_dict: Optional[dict] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        流式回答问题

        Args:
            question: 用户问题
            session_id: 会话ID
            k: 检索文档数量
            filter_dict: 过滤条件

        Yields:
            标准化流式事件
        """
        logger.info(f"流式处理问题: {question[:50]}...")

        try:
            retrieval = self.retriever.retrieve_with_diagnostics(question, k=k, filter_dict=filter_dict)
            docs = retrieval["documents"]
            low_confidence = retrieval["low_confidence"]
            best_score = retrieval["best_score"]
            sources = self.serialize_sources(docs)
            used_chat_mode = not docs

            yield {
                "type": "start",
                "message": "RAG开始处理",
                "session_id": session_id,
            }

            if sources:
                yield {
                    "type": "retrieval",
                    "sources": sources,
                }

            answer_parts: List[str] = []

            if used_chat_mode:
                messages = self._build_chat_messages(question, session_id)
                async for chunk in self.llm_client.chat_stream(messages):
                    answer_parts.append(chunk)
                    yield {
                        "type": "content",
                        "content": chunk,
                    }
                context = ""
            else:
                context = self.retriever.format_context(docs)
                async for chunk in self.llm_client.generate_with_context_stream(question, context):
                    answer_parts.append(chunk)
                    yield {
                        "type": "content",
                        "content": chunk,
                    }

                if low_confidence:
                    notice = self.build_low_confidence_notice(best_score)
                    suffix = f"\n\n{notice}"
                    answer_parts.append(suffix)
                    yield {
                        "type": "content",
                        "content": suffix,
                    }

            answer = "".join(answer_parts).strip()

            if session_id:
                self._save_conversation(session_id, question, answer, context)

            yield {
                "type": "end",
                "question": question,
                "answer": answer,
                "session_id": session_id,
                "sources": sources,
                "tool_calls": [],
                "tool_calls_count": 0,
                "debug_info": {
                    "requested_k": k,
                    "applied_category": filter_dict.get("category") if filter_dict else None,
                    "retrieval_count": len(docs),
                    "used_chat_mode": used_chat_mode,
                    "low_confidence": low_confidence,
                    "best_score": best_score,
                    "fallback_reason": "no_retrieval" if used_chat_mode else ("low_confidence" if low_confidence else None),
                    "retrieval_strategy": retrieval.get("retrieval_strategy"),
                    "vector_result_count": retrieval.get("vector_result_count", 0),
                    "keyword_result_count": retrieval.get("keyword_result_count", 0),
                    "merged_result_count": retrieval.get("merged_result_count", 0),
                    "rewritten_query": retrieval.get("rewritten_query"),
                },
            }
        except Exception as e:
            logger.error(f"流式回答问题失败: {e}")
            yield {
                "type": "error",
                "error": str(e),
            }

    def _chat_mode(self, question: str, session_id: Optional[str] = None) -> str:
        """
        聊天模式：直接使用LLM回答问题（不依赖检索）

        Args:
            question: 用户问题
            session_id: 会话ID（用于获取对话历史）

        Returns:
            AI回复
        """
        system_prompt = """你是一个专业的医疗助手，具备丰富的医学知识。
请遵循以下原则：
1. 回答要专业、准确、易懂
2. 如果涉及具体诊断或用药，请提醒用户咨询专业医生
3. 可以用通俗易懂的语言解释医学概念
4. 提供实用的健康建议
5. 承认知识局限性，不过度自信"""

        messages = self._build_chat_messages(question, session_id, system_prompt)

        try:
            answer = self.llm_client.chat(messages)
            logger.info("聊天模式回答完成")
            return answer
        except Exception as e:
            logger.error(f"聊天模式回答失败: {e}")
            return f"抱歉，我在生成回答时遇到了问题：{str(e)}"

    def _build_chat_messages(
        self,
        question: str,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """构建聊天模式消息列表"""
        system_prompt = system_prompt or """你是一个专业的医疗助手，具备丰富的医学知识。
请遵循以下原则：
1. 回答要专业、准确、易懂
2. 如果涉及具体诊断或用药，请提醒用户咨询专业医生
3. 可以用通俗易懂的语言解释医学概念
4. 提供实用的健康建议
5. 承认知识局限性，不过度自信"""

        messages = [{"role": "system", "content": system_prompt}]

        if session_id:
            recent_history = self._get_recent_conversation(session_id, limit=3)
            for hist in recent_history:
                messages.append({"role": "user", "content": hist['question']})
                messages.append({"role": "assistant", "content": hist['answer']})

        messages.append({"role": "user", "content": question})
        return messages

    def _get_recent_conversation(self, session_id: str, limit: int = 3) -> List:
        """
        获取最近的对话历史
            
        Args:
            session_id: 会话ID
            limit: 返回最近几条记录
                
        Returns:
            对话历史列表
        """
        try:
            from database.models import ConversationHistory
            from sqlalchemy import desc
                
            with get_db_session() as db:
                history = db.query(ConversationHistory)\
                    .filter(ConversationHistory.session_id == session_id)\
                    .order_by(desc(ConversationHistory.created_at))\
                    .limit(limit)\
                    .all()
                    
                # 在会话内提取所需数据，避免会话关闭后访问
                result = [
                    {
                        'question': h.question,
                        'answer': h.answer
                    }
                    for h in history
                ]
                    
                # 反转顺序，按时间正序排列
                return list(reversed(result))
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    def _save_conversation(
        self,
        session_id: str,
        question: str,
        answer: str,
        context: str
    ):
        """
        保存对话历史到数据库
        
        Args:
            session_id: 会话ID
            question: 问题
            answer: 回答
            context: 上下文
        """
        try:
            with get_db_session() as db:
                conversation = ConversationHistory(
                    session_id=session_id,
                    question=question,
                    answer=answer,
                    context=context,
                    record_type="rag"
                )
                db.add(conversation)
            logger.debug(f"对话历史已保存，session_id: {session_id}")
        except Exception as e:
            logger.error(f"保存对话历史失败: {e}")
            # 不抛出异常，避免影响主流程
    
    def delete_documents(self, doc_ids: List[str]) -> bool:
        """
        删除文档
        
        Args:
            doc_ids: 文档ID列表
            
        Returns:
            是否删除成功
        """
        try:
            return self.vector_store.delete_documents(doc_ids)
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise
    
    def get_collection_stats(self) -> Dict:
        """
        获取知识库统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 短TTL缓存：避免前端频繁刷新 stats 压垮 DB
            if getattr(settings, "ENABLE_STATS_CACHE", True):
                ttl_sec = max(int(getattr(settings, "STATS_CACHE_TTL_SEC", 15)), 0)
                if ttl_sec > 0:
                    # 兼容 tests 中通过 __new__ 构造的实例
                    if not hasattr(self, "_stats_cache_lock"):
                        self._stats_cache_lock = threading.Lock()
                        self._stats_cache_value = None
                        self._stats_cache_expires_at = 0.0

                    now = time.time()
                    with self._stats_cache_lock:
                        cached = getattr(self, "_stats_cache_value", None)
                        expires_at = float(getattr(self, "_stats_cache_expires_at", 0.0) or 0.0)
                        if isinstance(cached, dict) and expires_at > now:
                            logger.debug(
                                "stats cache hit, expires_in_sec={}",
                                round(expires_at - now, 3),
                            )
                            return cached

            category_breakdown: Dict[str, int] = {}
            total_files = 0
            vectorized_files = 0
            pending_files = 0
            document_chunks = 0
            category_count = 0
            last_updated = None
            total_versions = 0
            active_versions = 0
            latest_version_time = None
            failed_jobs = 0
            try:
                with get_db_session() as db:
                    non_deleted_query = db.query(KnowledgeBaseFile) \
                        .filter(KnowledgeBaseFile.status != "deleted")

                    total_versions = non_deleted_query.count()
                    active_records = db.query(KnowledgeBaseFile) \
                        .filter(KnowledgeBaseFile.is_current.is_(True)) \
                        .filter(KnowledgeBaseFile.status == "active") \
                        .all()
                    active_versions = len(active_records)
                    vectorized_files = active_versions
                    document_chunks = sum(record.chunk_count or 0 for record in active_records)

                    total_files = db.query(func.count(func.distinct(KnowledgeBaseFile.source_id))) \
                        .filter(KnowledgeBaseFile.status != "deleted") \
                        .scalar() or 0
                    pending_files = max(int(total_files) - active_versions, 0)

                    category_rows = db.query(
                        KnowledgeBaseFile.category,
                        func.count(func.distinct(KnowledgeBaseFile.source_id)),
                    ).filter(KnowledgeBaseFile.status != "deleted") \
                     .group_by(KnowledgeBaseFile.category) \
                     .all()
                    category_breakdown = {
                        category or "general": int(count or 0)
                        for category, count in category_rows
                    }
                    category_count = len(category_breakdown)

                    latest_file = db.query(KnowledgeBaseFile) \
                        .filter(KnowledgeBaseFile.status != "deleted") \
                        .order_by(KnowledgeBaseFile.updated_at.desc()) \
                        .first()
                    latest_version_time = latest_file.updated_at if latest_file else None
                    if latest_file:
                        last_updated = latest_file.ingested_at or latest_file.updated_at
                    failed_jobs = db.query(KnowledgeBaseIngestJob) \
                        .filter(KnowledgeBaseIngestJob.status == "failed") \
                        .count()
            except Exception as governance_error:
                logger.warning(f"读取知识库治理统计失败，回退到文件系统统计: {governance_error}")
                supported_extensions = {".pdf", ".docx", ".txt"}
                data_dir = self.document_loader.data_dir
                files = [
                    file_path for file_path in data_dir.rglob("*")
                    if file_path.is_file() and file_path.suffix.lower() in supported_extensions
                ]
                md5_checker = MD5Checker()

                for file_path in files:
                    if md5_checker.check_file_exists(str(file_path)):
                        vectorized_files += 1

                    category = file_path.parent.name if file_path.parent != data_dir else "general"
                    category_breakdown[category] = category_breakdown.get(category, 0) + 1

                    modified_at = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if last_updated is None or modified_at > last_updated:
                        last_updated = modified_at

                total_files = len(files)
                pending_files = max(total_files - vectorized_files, 0)
                category_count = len(category_breakdown)
                document_chunks = self.vector_store.count_documents()

            stats = {
                "collection_name": self.vector_store.collection_name,
                "embedding_model": self.embeddings.model_name,
                "llm_model": self.llm_client.model_name,
                "top_k": self.retriever.k,
                "total_files": int(total_files),
                "vectorized_files": vectorized_files,
                "pending_files": pending_files,
                "document_chunks": document_chunks,
                "category_count": category_count,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "category_breakdown": category_breakdown,
                "total_versions": total_versions,
                "active_versions": active_versions,
                "latest_version_time": latest_version_time.isoformat() if latest_version_time else None,
                "failed_jobs": failed_jobs,
            }

            if getattr(settings, "ENABLE_STATS_CACHE", True):
                ttl_sec = max(int(getattr(settings, "STATS_CACHE_TTL_SEC", 15)), 0)
                if ttl_sec > 0:
                    if not hasattr(self, "_stats_cache_lock"):
                        self._stats_cache_lock = threading.Lock()
                    with self._stats_cache_lock:
                        self._stats_cache_value = stats
                        self._stats_cache_expires_at = time.time() + ttl_sec
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise
