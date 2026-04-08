"""
检索器模块
提供文档检索功能
"""
from typing import List, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from rag.vector_store import MedicalVectorStore
from config import settings
from loguru import logger


class MedicalRetriever:
    """医疗文档检索器"""
    
    def __init__(
        self,
        vector_store: MedicalVectorStore = None,
        k: int = None,
        score_threshold: float = 0.7
    ):
        """
        初始化检索器
        
        Args:
            vector_store: 向量存储实例
            k: 返回结果数量
            score_threshold: 相似度阈值
        """
        self.vector_store = vector_store or MedicalVectorStore()
        self.k = k or settings.TOP_K
        self.score_threshold = score_threshold
        logger.info(f"检索器初始化完成 - k: {self.k}, threshold: {self.score_threshold}")

    def retrieve(self, query: str, filter_dict: Optional[dict] = None, k: int = None) -> List[Document]:
        """
        检索相关文档

        Args:
            query: 查询文本
            filter_dict: 过滤条件
            k: 返回结果数量（可选，覆盖默认值）

        Returns:
            相关文档列表
        """
        try:
            # 使用传入的k值，如果没有则使用默认值
            search_k = k if k is not None else self.k

            docs = self.vector_store.similarity_search(
                query=query,
                k=search_k,
                filter_dict=filter_dict
            )
            logger.info(f"检索到 {len(docs)} 个相关文档")
            return docs
        except Exception as e:
            logger.error(f"文档检索失败: {e}")
            raise

    def retrieve_with_score(
        self,
        query: str,
        filter_dict: Optional[dict] = None
    ) -> List[tuple]:
        """
        检索相关文档并返回相似度分数
        
        Args:
            query: 查询文本
            filter_dict: 过滤条件
            
        Returns:
            (文档, 分数) 元组列表
        """
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=self.k,
                filter_dict=filter_dict
            )
            
            # 过滤低于阈值的結果
            filtered_results = [
                (doc, score) for doc, score in results
                if score >= self.score_threshold
            ]
            
            logger.info(f"检索到 {len(filtered_results)} 个相关文档（阈值: {self.score_threshold}）")
            return filtered_results
        except Exception as e:
            logger.error(f"带分数文档检索失败: {e}")
            raise
    
    def format_context(self, documents: List[Document]) -> str:
        """
        将检索到的文档格式化为上下文文本
        
        Args:
            documents: 文档列表
            
        Returns:
            格式化后的上下文文本
        """
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get('source', '未知来源')
            context_parts.append(
                f"[文档{i}] 来源: {source}\n{doc.page_content}"
            )
        
        context = "\n\n".join(context_parts)
        logger.debug(f"上下文格式化完成，长度: {len(context)} 字符")
        return context
