"""
文本分割器模块
将长文档分割成适合向量化的文本块
"""
import hashlib
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import settings
from loguru import logger


class MedicalTextSplitter:
    """医疗文本分割器"""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        初始化文本分割器
        
        Args:
            chunk_size: 每个文本块的大小
            chunk_overlap: 文本块之间的重叠大小
        """
        self.chunk_size = settings.CHUNK_SIZE if chunk_size is None else chunk_size
        self.chunk_overlap = settings.CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",  # 段落
                "\n",    # 换行
                "。",     # 句号
                "！",    # 感叹号
                "？",    # 问号
                "；",    # 分号
                "，",    # 逗号
                " ",     # 空格
                ""       # 字符
            ]
        )
        logger.info(f"文本分割器初始化完成 - chunk_size: {self.chunk_size}, chunk_overlap: {self.chunk_overlap}")

    @staticmethod
    def _build_chunk_id(source_key: str, page: str, chunk_index: int) -> str:
        """为每个文本块生成稳定且可追踪的ID。"""
        digest = hashlib.md5(f"{source_key}|{page}|{chunk_index}".encode("utf-8")).hexdigest()[:12]
        return f"chunk_{digest}_{chunk_index}"

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        分割文档列表
        
        Args:
            documents: 待分割的文档列表
            
        Returns:
            分割后的文档列表
        """
        try:
            split_docs = self.text_splitter.split_documents(documents)

            chunk_counters = {}
            for doc in split_docs:
                source_key = doc.metadata.get("source_path") or doc.metadata.get("source") or "unknown"
                page = str(doc.metadata.get("page", "na"))
                counter_key = f"{source_key}|{page}"
                chunk_index = chunk_counters.get(counter_key, 0) + 1
                chunk_counters[counter_key] = chunk_index

                doc.metadata["chunk_index"] = chunk_index
                doc.metadata["chunk_id"] = doc.metadata.get("chunk_id") or self._build_chunk_id(
                    source_key=source_key,
                    page=page,
                    chunk_index=chunk_index
                )

            logger.info(f"文档分割完成: {len(documents)} -> {len(split_docs)} 个文本块")
            return split_docs
        except Exception as e:
            logger.error(f"文档分割失败: {e}")
            raise
    
    def split_text(self, text: str) -> List[str]:
        """
        分割纯文本
        
        Args:
            text: 待分割的文本
            
        Returns:
            分割后的文本列表
        """
        try:
            chunks = self.text_splitter.split_text(text)
            logger.info(f"文本分割完成: {len(text)} 字符 -> {len(chunks)} 个文本块")
            return chunks
        except Exception as e:
            logger.error(f"文本分割失败: {e}")
            raise
