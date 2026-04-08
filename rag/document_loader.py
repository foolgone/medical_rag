"""
文档加载器模块
支持PDF、Word、TXT等格式的医疗文档加载
"""
from pathlib import Path
from typing import List, Dict, Tuple
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    DirectoryLoader
)
from langchain_core.documents import Document
from loguru import logger
from rag.md5_checker import MD5Checker


class MedicalDocumentLoader:
    """医疗文档加载器"""
    
    def __init__(self, data_dir: str = "data/medical_docs", enable_md5_check: bool = True):
        """
        初始化文档加载器
        
        Args:
            data_dir: 文档目录路径
            enable_md5_check: 是否启用MD5去重检查
        """
        self.data_dir = Path(data_dir)
        self.enable_md5_check = enable_md5_check
        self.md5_checker = MD5Checker() if enable_md5_check else None
        
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
    
    def load_directory(self, pattern: str = "**/*") -> Tuple[List[Document], int, int]:
        """
        加载目录下所有支持的文档（支持MD5去重）
        
        Args:
            pattern: 文件匹配模式
            
        Returns:
            (文档列表, 成功加载数量, 跳过数量)
        """
        all_documents = []
        success_count = 0
        skip_count = 0
        
        # 加载PDF文件
        pdf_files = list(self.data_dir.glob("**/*.pdf"))
        for pdf_file in pdf_files:
            if self.enable_md5_check and self.md5_checker.check_file_exists(str(pdf_file)):
                logger.info(f"跳过已存在的PDF: {pdf_file.name}")
                skip_count += 1
                continue
            
            docs = self.load_pdf(str(pdf_file))
            if docs:
                all_documents.extend(docs)
                if self.enable_md5_check:
                    self.md5_checker.add_file_record(str(pdf_file))
                success_count += 1
        
        # 加载Word文件
        docx_files = list(self.data_dir.glob("**/*.docx"))
        for docx_file in docx_files:
            if self.enable_md5_check and self.md5_checker.check_file_exists(str(docx_file)):
                logger.info(f"跳过已存在的Word: {docx_file.name}")
                skip_count += 1
                continue
            
            docs = self.load_docx(str(docx_file))
            if docs:
                all_documents.extend(docs)
                if self.enable_md5_check:
                    self.md5_checker.add_file_record(str(docx_file))
                success_count += 1
        
        # 加载TXT文件
        txt_files = list(self.data_dir.glob("**/*.txt"))
        for txt_file in txt_files:
            if self.enable_md5_check and self.md5_checker.check_file_exists(str(txt_file)):
                logger.info(f"跳过已存在的TXT: {txt_file.name}")
                skip_count += 1
                continue
            
            docs = self.load_txt(str(txt_file))
            if docs:
                all_documents.extend(docs)
                if self.enable_md5_check:
                    self.md5_checker.add_file_record(str(txt_file))
                success_count += 1
        
        logger.info(f"文档加载完成 - 成功: {success_count}, 跳过: {skip_count}, 总文档块: {len(all_documents)}")
        return all_documents, success_count, skip_count
    
    def load_single_file(self, file_path: str) -> Tuple[List[Document], bool]:
        """
        加载单个文件（支持MD5去重）
        
        Args:
            file_path: 文件路径
            
        Returns:
            (文档列表, 是否为新文件)
        """
        file_path = Path(file_path)
        
        # MD5检查
        if self.enable_md5_check and self.md5_checker.check_file_exists(str(file_path)):
            logger.info(f"文件已存在，跳过: {file_path.name}")
            return [], False
        
        # 根据文件扩展名加载
        suffix = file_path.suffix.lower()
        if suffix == '.pdf':
            docs = self.load_pdf(str(file_path))
        elif suffix == '.docx':
            docs = self.load_docx(str(file_path))
        elif suffix == '.txt':
            docs = self.load_txt(str(file_path))
        else:
            logger.error(f"不支持的文件格式: {suffix}")
            return [], False
        
        # 记录MD5
        if docs and self.enable_md5_check:
            self.md5_checker.add_file_record(str(file_path))
        
        return docs, len(docs) > 0
    
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
