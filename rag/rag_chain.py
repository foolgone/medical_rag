"""
RAG链核心逻辑
整合检索和生成，提供完整的问答流程
"""
from typing import List, Optional, Dict
from langchain_core.documents import Document
from rag.document_loader import MedicalDocumentLoader
from rag.text_splitter import MedicalTextSplitter
from rag.vector_store import MedicalVectorStore, MedicalEmbeddings
from rag.retriever import MedicalRetriever
from llm.ollama_client import MedicalLLMClient
from database.connection import get_db_session
from database.models import ConversationHistory
from loguru import logger
import uuid


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
        
        logger.info("医疗RAG链初始化完成")
    
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
            logger.info(f"开始导入文档，目录: {data_dir or 'default'}")
            
            # 加载文档
            if data_dir:
                self.document_loader.data_dir = data_dir
            documents = self.document_loader.load_directory()
            
            if not documents:
                logger.warning("没有找到可导入的文档")
                return 0
            
            # 添加元数据
            documents = self.document_loader.add_metadata(documents, category)
            
            # 分割文档
            split_docs = self.text_splitter.split_documents(documents)
            
            # 存储到向量数据库
            doc_ids = self.vector_store.add_documents(split_docs)
            
            logger.info(f"成功导入 {len(doc_ids)} 个文档块到知识库")
            return len(doc_ids)
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
            docs = self.retriever.retrieve(question, k=k, filter_dict=filter_dict)

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

            # 保存对话历史
            if session_id:
                self._save_conversation(session_id, question, answer, context)

            result = {
                "question": question,
                "answer": answer,
                "context_count": len(docs),
                "sources": [
                    {
                        "content": doc.page_content[:200],
                        "source": doc.metadata.get("source", "未知"),
                        "category": doc.metadata.get("category", "未知")
                    }
                    for doc in docs
                ]
            }

            logger.info("问题回答完成")
            return result
        except Exception as e:
            logger.error(f"回答问题失败: {e}")
            raise

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

        messages = [{"role": "system", "content": system_prompt}]

        # 如果有会话ID，尝试加载最近的对话历史
        if session_id:
            recent_history = self._get_recent_conversation(session_id, limit=3)
            for hist in recent_history:
                messages.append({"role": "user", "content": hist['question']})
                messages.append({"role": "assistant", "content": hist['answer']})

        messages.append({"role": "user", "content": question})

        try:
            answer = self.llm_client.chat(messages)
            logger.info("聊天模式回答完成")
            return answer
        except Exception as e:
            logger.error(f"聊天模式回答失败: {e}")
            return f"抱歉，我在生成回答时遇到了问题：{str(e)}"

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
                    context=context
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
            # 这里可以根据实际需求实现统计逻辑
            stats = {
                "collection_name": self.vector_store.collection_name,
                "embedding_model": self.embeddings.model_name,
                "llm_model": self.llm_client.model_name,
                "top_k": self.retriever.k
            }
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise
