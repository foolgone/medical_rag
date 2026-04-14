"""
检索器模块
提供文档检索功能
"""
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document
from rag.bm25_retriever import LightweightBM25Retriever
from rag.reranker import LightweightReranker
from rag.vector_store import MedicalVectorStore
from config import settings
from loguru import logger


class MedicalRetriever:
    """医疗文档检索器"""
    
    def __init__(
        self,
        vector_store: MedicalVectorStore = None,
        k: int = None,
        score_threshold: float = 0.7,
        low_confidence_threshold: float = None
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
        self.hybrid_threshold = (
            low_confidence_threshold
            if low_confidence_threshold is not None
            else getattr(settings, "LOW_CONFIDENCE_THRESHOLD", 0.35)
        )
        self.keyword_retriever = LightweightBM25Retriever(self.vector_store)
        self.reranker = LightweightReranker(top_k=self.k)
        logger.info(
            f"检索器初始化完成 - k: {self.k}, threshold: {self.score_threshold}, "
            f"low_confidence_threshold: {self.hybrid_threshold}"
        )

    @staticmethod
    def _normalize_score(raw_score: Optional[float]) -> Optional[float]:
        """
        将向量距离近似映射为 0 到 1 的可读分数。

        PGVector 返回的通常是“距离”，距离越小越相关。
        这里将其转换为越大越好的展示分数，便于前端显示与阈值判断。
        """
        if raw_score is None:
            return None

        normalized = 1 - float(raw_score)
        return max(0.0, min(1.0, normalized))

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
            diagnostics = self.retrieve_with_diagnostics(query=query, filter_dict=filter_dict, k=k)
            docs = diagnostics["documents"]
            logger.info(f"检索到 {len(docs)} 个相关文档")
            return docs
        except Exception as e:
            logger.error(f"文档检索失败: {e}")
            raise

    def retrieve_with_diagnostics(
        self,
        query: str,
        filter_dict: Optional[dict] = None,
        k: int = None
    ) -> Dict[str, Any]:
        """
        检索文档并返回诊断信息。

        Returns:
            {
                "documents": 最终用于回答的文档,
                "raw_documents": 原始检索到的文档,
                "low_confidence": 是否为低置信命中,
                "raw_result_count": 原始命中数,
                "best_score": 最佳归一化分数,
            }
        """
        search_k = k if k is not None else self.k
        candidate_k = max(search_k * 3, 10)
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=candidate_k,
            filter_dict=filter_dict
        )

        vector_documents: List[Document] = []
        best_vector_score: Optional[float] = None

        for doc, raw_score in results:
            normalized_score = self._normalize_score(raw_score)
            doc.metadata["raw_score"] = raw_score
            doc.metadata["score"] = normalized_score
            doc.metadata.setdefault("retrieval_methods", ["vector"])
            vector_documents.append(doc)

            if normalized_score is not None:
                best_vector_score = normalized_score if best_vector_score is None else max(best_vector_score, normalized_score)

        keyword_result = self.keyword_retriever.retrieve(query=query, filter_dict=filter_dict, k=candidate_k)
        keyword_documents: List[Document] = keyword_result["documents"]

        merged_documents: Dict[str, Document] = {}

        def build_doc_key(doc: Document) -> str:
            return (
                doc.metadata.get("chunk_id")
                or f"{doc.metadata.get('source', 'unknown')}|{doc.metadata.get('page')}|{hash(doc.page_content[:120])}"
            )

        for doc in vector_documents:
            key = build_doc_key(doc)
            merged_documents[key] = doc

        for doc in keyword_documents:
            key = build_doc_key(doc)
            existing = merged_documents.get(key)
            if existing:
                existing.metadata["keyword_score"] = doc.metadata.get("keyword_score")
                existing.metadata["keyword_score_norm"] = doc.metadata.get("keyword_score_norm")
                methods = set(existing.metadata.get("retrieval_methods", []))
                methods.add("keyword")
                existing.metadata["retrieval_methods"] = sorted(methods)
                continue

            doc.metadata.setdefault("score", 0.0)
            doc.metadata.setdefault("raw_score", None)
            doc.metadata.setdefault("retrieval_methods", ["keyword"])
            merged_documents[key] = doc

        reranked_documents = self.reranker.rerank(
            query=keyword_result["expanded_query"] or query,
            candidates=list(merged_documents.values()),
            query_tokens=keyword_result["query_tokens"],
            top_k=search_k,
        )

        best_score = None
        for doc in reranked_documents:
            rerank_score = doc.metadata.get("rerank_score")
            if rerank_score is not None:
                best_score = rerank_score if best_score is None else max(best_score, rerank_score)

        raw_documents = reranked_documents if reranked_documents else vector_documents
        confident_documents = [
            doc for doc in reranked_documents
            if doc.metadata.get("rerank_score", 0.0) >= self.hybrid_threshold
        ]

        low_confidence = bool(raw_documents) and not confident_documents
        documents = confident_documents if confident_documents else raw_documents

        logger.info(
            "混合检索完成 - 向量候选: {}, 关键词候选: {}, 合并后: {}, 高置信: {}, 低置信: {}",
            len(vector_documents),
            len(keyword_documents),
            len(merged_documents),
            len(confident_documents),
            low_confidence
        )

        return {
            "documents": documents,
            "raw_documents": raw_documents,
            "low_confidence": low_confidence,
            "raw_result_count": len(raw_documents),
            "best_score": best_score,
            "vector_result_count": len(vector_documents),
            "keyword_result_count": len(keyword_documents),
            "merged_result_count": len(merged_documents),
            "rewritten_query": keyword_result["expanded_query"],
            "query_tokens": keyword_result["query_tokens"],
            "best_vector_score": best_vector_score,
            "retrieval_strategy": "hybrid",
        }

    def retrieve_with_score(
        self,
        query: str,
        filter_dict: Optional[dict] = None,
        k: int = None
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
            diagnostics = self.retrieve_with_diagnostics(query=query, filter_dict=filter_dict, k=k)
            filtered_results = [
                (doc, doc.metadata.get("rerank_score", doc.metadata.get("score")))
                for doc in diagnostics["documents"]
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
