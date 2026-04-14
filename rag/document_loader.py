"""
文档加载器模块
支持PDF、Word、TXT等格式的医疗文档加载。

第 6 步后，文档加载器只负责“读取文件 + 补齐基础元数据”，
不再承担知识库生命周期治理判断，版本去重统一交给治理服务处理。
"""
from datetime import datetime
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional
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

    DEFAULT_DATA_DIR = "data/medical_docs"
    
    def __init__(self, data_dir: Optional[str] = DEFAULT_DATA_DIR, enable_md5_check: bool = True):
        """
        初始化文档加载器
        
        Args:
            data_dir: 文档目录路径
            enable_md5_check: 是否启用MD5去重检查
        """
        resolved_data_dir = data_dir or self.DEFAULT_DATA_DIR
        self.data_dir = Path(resolved_data_dir)
        self.enable_md5_check = enable_md5_check
        self.md5_checker = MD5Checker() if enable_md5_check else None
        self.last_load_summary: Dict[str, object] = {
            "success_count": 0,
            "skip_count": 0,
            "failed_count": 0,
            "failed_files": [],
            "document_count": 0,
            "loaded_files": [],
        }
        
        if not self.data_dir.exists():
            logger.warning(f"文档目录不存在: {resolved_data_dir}")
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
        加载目录下所有支持的文档。

        Args:
            pattern: 文件匹配模式
            
        Returns:
            (文档列表, 成功加载数量, 跳过数量)
        """
        all_documents = []
        success_count = 0
        skip_count = 0
        failed_files = []
        loaded_files = []
        
        # 第 6 步后，版本判断由知识库治理服务负责；
        # 这里不再使用 MD5 记录阻断文件读取。
        # 加载PDF文件
        pdf_files = list(self.data_dir.glob("**/*.pdf"))
        for pdf_file in pdf_files:
            docs = self.load_pdf(str(pdf_file))
            if docs:
                all_documents.extend(docs)
                success_count += 1
                loaded_files.append(str(pdf_file))
            else:
                failed_files.append(pdf_file.name)
        
        # 加载Word文件
        docx_files = list(self.data_dir.glob("**/*.docx"))
        for docx_file in docx_files:
            docs = self.load_docx(str(docx_file))
            if docs:
                all_documents.extend(docs)
                success_count += 1
                loaded_files.append(str(docx_file))
            else:
                failed_files.append(docx_file.name)
        
        # 加载TXT文件
        txt_files = list(self.data_dir.glob("**/*.txt"))
        for txt_file in txt_files:
            docs = self.load_txt(str(txt_file))
            if docs:
                all_documents.extend(docs)
                success_count += 1
                loaded_files.append(str(txt_file))
            else:
                failed_files.append(txt_file.name)
        
        self.last_load_summary = {
            "success_count": success_count,
            "skip_count": skip_count,
            "failed_count": len(failed_files),
            "failed_files": failed_files,
            "document_count": len(all_documents),
            "loaded_files": loaded_files,
        }
        logger.info(f"文档加载完成 - 成功: {success_count}, 跳过: {skip_count}, 总文档块: {len(all_documents)}")
        return all_documents, success_count, skip_count
    
    def load_single_file(self, file_path: str) -> Tuple[List[Document], bool]:
        """
        加载单个文件。

        Args:
            file_path: 文件路径
            
        Returns:
            (文档列表, 是否为新文件)
        """
        file_path = Path(file_path)
        
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
        
        return docs, len(docs) > 0

    def _infer_category_from_source(self, source_path: Optional[str]) -> Optional[str]:
        """根据文件路径推断分类目录。"""
        if not source_path:
            return None

        try:
            source = Path(source_path).resolve()
            data_dir = self.data_dir.resolve()
            parent = source.parent

            if parent == data_dir:
                return "general"

            relative_parent = parent.relative_to(data_dir)
            parts = relative_parent.parts
            if not parts:
                return "general"

            return parts[0]
        except Exception:
            return Path(source_path).parent.name or None

    @staticmethod
    def _normalize_page(page: Optional[object]) -> Optional[int]:
        """统一页码格式，PDF 场景从 0 基转为 1 基。"""
        if page is None:
            return None

        if isinstance(page, int):
            return page + 1 if page >= 0 else 1

        return None

    @staticmethod
    def _resolve_updated_at(source_path: Optional[str], existing_value: Optional[str]) -> Optional[str]:
        """优先复用已有时间，否则读取文件修改时间。"""
        if existing_value:
            return existing_value

        if not source_path:
            return None

        try:
            modified_at = datetime.fromtimestamp(Path(source_path).stat().st_mtime)
            return modified_at.isoformat()
        except Exception:
            return None

    def add_metadata(
        self,
        documents: List[Document],
        category: str = "general",
        file_metadata_map: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Document]:
        """
        为文档添加元数据
        
        Args:
            documents: 文档列表
            category: 文档分类
            
        Returns:
            添加了元数据的文档列表
        """
        file_metadata_map = file_metadata_map or {}
        for doc in documents:
            source_path = doc.metadata.get("source")
            source_name = Path(source_path).name if source_path else doc.metadata.get("source", "未知来源")
            inferred_category = self._infer_category_from_source(source_path)
            page = self._normalize_page(doc.metadata.get("page"))
            source_type = doc.metadata.get("source_type")
            metadata_override = file_metadata_map.get(str(source_path), {})

            if not source_type and source_path:
                source_type = Path(source_path).suffix.lower().lstrip(".") or "unknown"

            resolved_category = category
            if inferred_category and (not category or category == "general"):
                resolved_category = inferred_category

            doc.metadata.update({
                "source": source_name,
                "source_path": source_path,
                "category": metadata_override.get("category", resolved_category or inferred_category or "general"),
                "page": page,
                "source_type": metadata_override.get("source_type", source_type or "unknown"),
                "updated_at": metadata_override.get(
                    "updated_at",
                    self._resolve_updated_at(source_path, doc.metadata.get("updated_at"))
                ),
            })
            doc.metadata.update(metadata_override)
        return documents
