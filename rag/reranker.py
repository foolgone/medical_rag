"""
轻量重排器

基于向量分数、关键词分数和词项重叠做线性融合，避免引入额外模型依赖。
"""
from typing import List, Optional

from langchain_core.documents import Document

from rag.bm25_retriever import LightweightBM25Retriever


class LightweightReranker:
    """对候选块做轻量重排。"""

    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    @staticmethod
    def _lexical_overlap_score(query_tokens: List[str], content: str) -> float:
        """用词项重叠衡量文本与查询的显式匹配程度。"""
        if not query_tokens:
            return 0.0

        content_tokens = set(LightweightBM25Retriever.tokenize(content))
        if not content_tokens:
            return 0.0

        overlap = sum(1 for token in set(query_tokens) if token in content_tokens)
        return overlap / max(len(set(query_tokens)), 1)

    def rerank(
        self,
        query: str,
        candidates: List[Document],
        query_tokens: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> List[Document]:
        """对候选文档按融合分数排序。"""
        query_tokens = query_tokens or LightweightBM25Retriever.tokenize(query)
        reranked: List[Document] = []

        for doc in candidates:
            vector_score = float(doc.metadata.get("score") or 0.0)
            keyword_score = float(doc.metadata.get("keyword_score_norm") or 0.0)
            overlap_score = self._lexical_overlap_score(query_tokens, doc.page_content)

            bonus = 0.0
            if any(token and token in doc.page_content.lower() for token in query_tokens if len(token) >= 2):
                bonus = 0.05

            rerank_score = 0.45 * vector_score + 0.35 * keyword_score + 0.20 * overlap_score + bonus
            doc.metadata["overlap_score"] = overlap_score
            doc.metadata["rerank_score"] = min(rerank_score, 1.0)
            reranked.append(doc)

        reranked.sort(key=lambda item: item.metadata.get("rerank_score", 0.0), reverse=True)
        return reranked[:(top_k or self.top_k)]
