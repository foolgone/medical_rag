"""
轻量关键词检索器

不依赖额外第三方 BM25 库，使用简化 BM25 思路对已入库文档块做关键词召回。
"""
import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

from langchain_core.documents import Document
from loguru import logger

from rag.vector_store import MedicalVectorStore


class LightweightBM25Retriever:
    """基于向量库已入库文本的轻量关键词检索器。"""

    MEDICAL_SYNONYMS: Dict[str, List[str]] = {
        "发烧": ["发热", "体温升高"],
        "头疼": ["头痛"],
        "嗓子疼": ["咽痛", "喉咙痛"],
        "流鼻涕": ["鼻塞", "流涕"],
        "感冒": ["普通感冒", "上呼吸道感染"],
        "血压高": ["高血压"],
        "血糖高": ["糖尿病", "高血糖"],
        "拉肚子": ["腹泻"],
        "肚子疼": ["腹痛"],
        "咳": ["咳嗽"],
        "药": ["药物", "用药"],
    }

    STOPWORDS = {
        "怎么", "怎么办", "什么", "如何", "需要", "应该", "可以", "一下",
        "一下子", "请问", "我", "我想", "有点", "这个", "那个", "以及",
        "the", "a", "an", "is", "are", "to", "of", "and",
    }

    def __init__(self, vector_store: MedicalVectorStore):
        self.vector_store = vector_store

    @classmethod
    def normalize_query(cls, query: str) -> Tuple[str, List[str]]:
        """对用户口语问题做轻量归一和同义扩展。"""
        normalized = (query or "").strip().lower()
        expanded_terms: List[str] = []

        for source, targets in cls.MEDICAL_SYNONYMS.items():
            if source in normalized:
                expanded_terms.extend(targets)

        deduped_terms: List[str] = []
        seen = set()
        for term in [normalized, *expanded_terms]:
            if term and term not in seen:
                seen.add(term)
                deduped_terms.append(term)

        expanded_query = " ".join(deduped_terms)
        tokens = cls.tokenize(expanded_query)
        return expanded_query, tokens

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """兼容英文词、数字以及中文 2-3 gram 的分词方式。"""
        text = (text or "").lower()
        latin_tokens = re.findall(r"[a-z0-9]+", text)
        chinese_sequences = re.findall(r"[\u4e00-\u9fff]+", text)

        tokens: List[str] = []
        for token in latin_tokens:
            if token not in cls.STOPWORDS:
                tokens.append(token)

        for seq in chinese_sequences:
            if len(seq) == 1:
                if seq not in cls.STOPWORDS:
                    tokens.append(seq)
                continue

            for n in (2, 3):
                if len(seq) < n:
                    continue
                for index in range(len(seq) - n + 1):
                    gram = seq[index:index + n]
                    if gram not in cls.STOPWORDS:
                        tokens.append(gram)

        return tokens

    @classmethod
    def _bm25_score(
        cls,
        doc_tokens: List[str],
        query_tokens: List[str],
        document_frequencies: Dict[str, int],
        avg_doc_length: float,
        corpus_size: int,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> float:
        """简化 BM25 打分。"""
        if not doc_tokens or not query_tokens or corpus_size == 0:
            return 0.0

        doc_length = len(doc_tokens)
        term_frequencies = Counter(doc_tokens)
        score = 0.0

        for term in query_tokens:
            tf = term_frequencies.get(term, 0)
            if tf == 0:
                continue

            df = document_frequencies.get(term, 0)
            idf = math.log(1 + (corpus_size - df + 0.5) / (df + 0.5))
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_length / max(avg_doc_length, 1))
            score += idf * (numerator / denominator)

        return score

    def retrieve(
        self,
        query: str,
        filter_dict: Optional[dict] = None,
        k: int = 10
    ) -> Dict[str, object]:
        """
        执行关键词召回。

        Returns:
            {
                "documents": 文档列表,
                "expanded_query": 改写后的查询,
                "query_tokens": 查询 token 列表,
            }
        """
        expanded_query, query_tokens = self.normalize_query(query)
        documents = self.vector_store.fetch_documents(filter_dict=filter_dict)

        if not documents or not query_tokens:
            return {
                "documents": [],
                "expanded_query": expanded_query,
                "query_tokens": query_tokens,
            }

        tokenized_docs: List[Tuple[Document, List[str]]] = []
        document_frequencies: Counter = Counter()

        for doc in documents:
            tokens = self.tokenize(doc.page_content)
            tokenized_docs.append((doc, tokens))
            document_frequencies.update(set(tokens))

        avg_doc_length = sum(len(tokens) for _, tokens in tokenized_docs) / max(len(tokenized_docs), 1)
        scored_docs: List[Document] = []
        best_score = 0.0

        for doc, tokens in tokenized_docs:
            keyword_score = self._bm25_score(
                doc_tokens=tokens,
                query_tokens=query_tokens,
                document_frequencies=document_frequencies,
                avg_doc_length=avg_doc_length,
                corpus_size=len(tokenized_docs),
            )

            if keyword_score <= 0:
                continue

            cloned = Document(page_content=doc.page_content, metadata=dict(doc.metadata))
            cloned.metadata["keyword_score"] = keyword_score
            scored_docs.append(cloned)
            best_score = max(best_score, keyword_score)

        if best_score > 0:
            for doc in scored_docs:
                doc.metadata["keyword_score_norm"] = doc.metadata["keyword_score"] / best_score

        scored_docs.sort(key=lambda item: item.metadata.get("keyword_score", 0.0), reverse=True)
        top_docs = scored_docs[:k]

        logger.info(
            "关键词检索完成 - 查询token数: {}, 原始候选: {}, 返回: {}",
            len(query_tokens),
            len(scored_docs),
            len(top_docs),
        )

        return {
            "documents": top_docs,
            "expanded_query": expanded_query,
            "query_tokens": query_tokens,
        }
