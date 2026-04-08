"""
文档加载器模块
支持PDF、Word、TXT等格式的医疗文档加载
"""
from pathlib import Path
from typing import List, Dict
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    DirectoryLoader
)
from langchain_core.documents import Document
from loguru import logger


class MedicalDocumentLoader:
    """医疗文档加载器"""
    
    def __init__(self, data_dir: str = "data/medical_docs"):
        """
        初始化文档加载器
        
        Args:
            data_dir: 文档目录路径
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            logger.warning(f"文档目录不存在: {data_dir}")
            self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_pdf(self, file_path: str) -> List[Document]:
        """加载PDF文档"""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            logger.info(f"成功加载PDF: {file_path}, 共{len(documents)}页")
            return documents
        except Exception as e:
            logger.error(f"加载PDF失败 {file_path}: {e}")
            return []
    
    def load_docx(self, file_path: str) -> List[Document]:
        """加载Word文档"""
        try:
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
            logger.info(f"成功加载Word: {file_path}, 共{len(documents)}个文档")
            return documents
        except Exception as e:
            logger.error(f"加载Word失败 {file_path}: {e}")
            return []
    
    def load_txt(self, file_path: str) -> List[Document]:
        """加载TXT文档"""
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
            logger.info(f"成功加载TXT: {file_path}")
            return documents
        except Exception as e:
            logger.error(f"加载TXT失败 {file_path}: {e}")
            return []
    
    def load_directory(self, pattern: str = "**/*") -> List[Document]:
        """
        加载目录下所有支持的文档
        
        Args:
            pattern: 文件匹配模式
            
        Returns:
            文档列表
        """
        all_documents = []
        
        # 加载PDF文件
        pdf_files = list(self.data_dir.glob("**/*.pdf"))
        for pdf_file in pdf_files:
            docs = self.load_pdf(str(pdf_file))
            all_documents.extend(docs)
        
        # 加载Word文件
        docx_files = list(self.data_dir.glob("**/*.docx"))
        for docx_file in docx_files:
            docs = self.load_docx(str(docx_file))
            all_documents.extend(docs)
        
        # 加载TXT文件
        txt_files = list(self.data_dir.glob("**/*.txt"))
        for txt_file in txt_files:
            docs = self.load_txt(str(txt_file))
            all_documents.extend(docs)
        
        logger.info(f"总共加载 {len(all_documents)} 个文档")
        return all_documents
    
    def add_metadata(self, documents: List[Document], category: str = "general") -> List[Document]:
        """
        为文档添加元数据
        
        Args:
            documents: 文档列表
            category: 文档分类
            
        Returns:
            添加了元数据的文档列表
        """
        for doc in documents:
            doc.metadata.update({
                "category": category,
                "source_type": "medical"
            })
        return documents
