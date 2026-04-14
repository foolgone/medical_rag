"""
嵌入模型和向量存储模块
使用Ollama提供嵌入服务，PostgreSQL存储向量
"""
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
from config import settings
from database.connection import engine
from loguru import logger


class MedicalEmbeddings:
    """医疗文档嵌入模型"""
    
    def __init__(self, model_name: str = None, base_url: str = None):
        """
        初始化嵌入模型
        
        Args:
            model_name: 嵌入模型名称
            base_url: Ollama服务地址
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        
        self.embeddings = OllamaEmbeddings(
            model=self.model_name,
            base_url=self.base_url
        )
        logger.info(f"嵌入模型初始化完成: {self.model_name}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        为多个文档生成嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        try:
            embeddings = self.embeddings.embed_documents(texts)
            logger.info(f"成功生成 {len(embeddings)} 个文档嵌入")
            return embeddings
        except Exception as e:
            logger.error(f"生成文档嵌入失败: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        为查询文本生成嵌入向量
        
        Args:
            text: 查询文本
            
        Returns:
            嵌入向量
        """
        try:
            embedding = self.embeddings.embed_query(text)
            logger.debug(f"成功生成查询嵌入，维度: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"生成查询嵌入失败: {e}")
            raise


class MedicalVectorStore:
    """医疗文档向量存储"""
    
    def __init__(
        self,
        connection: str = None,
        collection_name: str = "medical_documents",
        embeddings: MedicalEmbeddings = None
    ):
        """
        初始化向量存储
        
        Args:
            connection: 数据库连接字符串
            collection_name: 集合名称
            embeddings: 嵌入模型实例
        """
        self.connection = connection or settings.DATABASE_URL
        self.collection_name = collection_name
        self.embeddings = embeddings or MedicalEmbeddings()
        
        # 初始化PGVector存储
        self.vector_store = PGVector(
            embeddings=self.embeddings.embeddings,
            collection_name=self.collection_name,
            connection=self.connection,
            use_jsonb=True
        )
        logger.info(f"向量存储初始化完成: {self.collection_name}")
    
    def add_documents(self, documents: List, ids: Optional[List[str]] = None) -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表
            ids: 文档ID列表（可选）
            
        Returns:
            添加的文档ID列表
        """
        try:
            if ids:
                doc_ids = self.vector_store.add_documents(documents, ids=ids)
            else:
                doc_ids = self.vector_store.add_documents(documents)
            
            logger.info(f"成功添加 {len(doc_ids)} 个文档到向量存储")
            return doc_ids
        except Exception as e:
            logger.error(f"添加文档到向量存储失败: {e}")
            raise
    
    def delete_documents(self, ids: List[str]) -> bool:
        """
        从向量存储删除文档
        
        Args:
            ids: 要删除的文档ID列表
            
        Returns:
            是否删除成功
        """
        try:
            self.vector_store.delete(ids=ids)
            logger.info(f"成功删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def similarity_search(
        self,
        query: str,
        k: int = None,
        filter_dict: Optional[dict] = None
    ) -> List:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            相似文档列表
        """
        try:
            k = k or settings.TOP_K
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter_dict
            )
            logger.debug(f"相似度搜索完成，找到 {len(results)} 个相关文档")
            return results
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            raise
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = None,
        filter_dict: Optional[dict] = None
    ) -> List:
        """
        带分数的相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            (文档, 分数) 元组列表
        """
        try:
            k = k or settings.TOP_K
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict
            )
            logger.debug(f"带分数相似度搜索完成，找到 {len(results)} 个相关文档")
            return results
        except Exception as e:
            logger.error(f"带分数相似度搜索失败: {e}")
            raise

    @staticmethod
    def _parse_metadata(metadata: Any) -> Dict[str, Any]:
        """兼容 psycopg 返回 dict / JSON 字符串两种情况。"""
        if isinstance(metadata, dict):
            return metadata

        if isinstance(metadata, str):
            try:
                return json.loads(metadata)
            except Exception:
                return {}

        return {}

    def fetch_documents(
        self,
        filter_dict: Optional[dict] = None,
        limit: Optional[int] = None
    ) -> List[Document]:
        """
        从向量库读取已入库文档块，供关键词检索等离线打分使用。

        Args:
            filter_dict: 元数据过滤条件
            limit: 限制返回数量

        Returns:
            文档列表
        """
        sql = """
            SELECT e.id, e.document, e.cmetadata
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = :collection_name
        """

        params: Dict[str, Any] = {"collection_name": self.collection_name}

        if filter_dict and filter_dict.get("category"):
            sql += " AND e.cmetadata->>'category' = :category"
            params["category"] = filter_dict["category"]

        sql += " ORDER BY e.id"

        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = limit

        try:
            documents: List[Document] = []
            with engine.connect() as conn:
                rows = conn.execute(text(sql), params).mappings().all()

            for row in rows:
                metadata = self._parse_metadata(row.get("cmetadata"))
                metadata.setdefault("chunk_id", row.get("id"))
                documents.append(
                    Document(
                        page_content=row.get("document") or "",
                        metadata=metadata
                    )
                )

            logger.debug(f"从向量库读取 {len(documents)} 个文档块用于关键词检索")
            return documents
        except Exception as e:
            logger.error(f"读取向量库文档失败: {e}")
            return []

    def count_documents(self) -> int:
        """
        统计当前集合中的文档块数量

        Returns:
            文档块数量
        """
        sql = text(
            """
            SELECT COUNT(*)
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = :collection_name
            """
        )

        try:
            with engine.connect() as conn:
                count = conn.execute(sql, {"collection_name": self.collection_name}).scalar()
            return int(count or 0)
        except Exception as e:
            logger.warning(f"统计向量文档块失败: {e}")
            return 0
