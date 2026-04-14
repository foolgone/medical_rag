"""
知识库更新服务模块
提供增量更新、全量更新等功能
"""
from typing import Dict, List, Optional
from pathlib import Path
from rag.document_loader import MedicalDocumentLoader
from rag.text_splitter import MedicalTextSplitter
from loguru import logger


class KnowledgeBaseUpdateService:
    """知识库更新服务"""
    
    def __init__(self, rag_chain):
        """
        初始化更新服务
        
        Args:
            rag_chain: RAG链实例
        """
        self.rag_chain = rag_chain
        logger.info("知识库更新服务初始化完成")

    @staticmethod
    def _build_loader(data_dir: Optional[str], enable_md5_check: bool) -> MedicalDocumentLoader:
        """创建文档加载器，并在传入目录时覆盖默认目录。"""
        loader = MedicalDocumentLoader(enable_md5_check=enable_md5_check)
        if data_dir:
            loader.data_dir = Path(data_dir)
        return loader

    @staticmethod
    def _build_result_message(
        ingested_count: int,
        skip_count: int,
        failed_count: int,
        failed_files: List[str],
    ) -> str:
        """拼接更新结果提示，明确区分文档块、跳过文件和失败文件。"""
        message = f"成功导入 {ingested_count} 个文档块，跳过 {skip_count} 个已存在文件"
        if failed_count:
            preview = "、".join(failed_files[:3])
            suffix = f"，另有 {failed_count} 个文件加载失败"
            if preview:
                suffix += f"（{preview}）"
            message += suffix
        return message
    
    def incremental_update(self, data_dir: Optional[str] = None, category: str = "general") -> Dict:
        """
        增量更新：仅导入新增文件
        
        Args:
            data_dir: 文档目录
            category: 文档分类
            
        Returns:
            更新结果统计
        """
        try:
            logger.info(f"开始增量更新知识库，目录: {data_dir or 'default'}")
            
            # 使用MD5检查，只加载新文件
            loader = self._build_loader(data_dir, enable_md5_check=True)
            
            # 加载文档（自动跳过已存在的）
            documents, success_count, skip_count = loader.load_directory()
            load_summary = loader.last_load_summary
            failed_count = load_summary.get("failed_count", 0)
            failed_files = load_summary.get("failed_files", [])
            
            if not documents:
                if failed_count:
                    message = self._build_result_message(0, skip_count, failed_count, failed_files)
                    logger.warning(f"增量更新未导入新文档: {message}")
                    return {
                        "success": False,
                        "ingested_count": 0,
                        "skipped_count": skip_count,
                        "message": message
                    }

                logger.info("没有新文件需要导入")
                return {
                    "success": True,
                    "ingested_count": 0,
                    "skipped_count": skip_count,
                    "message": "没有新文件需要导入"
                }
            
            # 添加元数据
            documents = loader.add_metadata(documents, category)
            
            # 分割文档
            splitter = MedicalTextSplitter()
            split_docs = splitter.split_documents(documents)
            
            # 存储到向量数据库
            doc_ids = self.rag_chain.vector_store.add_documents(split_docs)
            
            result = {
                "success": len(doc_ids) > 0 or failed_count == 0,
                "ingested_count": len(doc_ids),
                "skipped_count": skip_count,
                "file_count": success_count,
                "message": self._build_result_message(len(doc_ids), skip_count, failed_count, failed_files)
            }
            
            logger.info(f"增量更新完成: {result}")
            return result
        except Exception as e:
            logger.error(f"增量更新失败: {e}")
            return {
                "success": False,
                "ingested_count": 0,
                "skipped_count": 0,
                "message": f"更新失败: {str(e)}"
            }
    
    def full_update(self, data_dir: Optional[str] = None, category: str = "general", clear_first: bool = False) -> Dict:
        """
        全量更新：重新导入所有文件
        
        Args:
            data_dir: 文档目录
            category: 文档分类
            clear_first: 是否先清空现有数据
            
        Returns:
            更新结果统计
        """
        try:
            logger.info(f"开始全量更新知识库，目录: {data_dir or 'default'}")
            
            # 如果需要，先清空
            if clear_first:
                logger.info("清空现有知识库数据")
                # 这里可以添加清空逻辑
            
            # 不使用MD5检查，强制重新加载
            loader = self._build_loader(data_dir, enable_md5_check=False)
            
            # 加载所有文档
            documents, _, _ = loader.load_directory()
            load_summary = loader.last_load_summary
            failed_count = load_summary.get("failed_count", 0)
            failed_files = load_summary.get("failed_files", [])
            
            if not documents:
                if failed_count:
                    preview = "、".join(failed_files[:3])
                    message = f"没有找到可导入的文档，且有 {failed_count} 个文件加载失败"
                    if preview:
                        message += f"（{preview}）"
                    logger.warning(message)
                    return {
                        "success": False,
                        "ingested_count": 0,
                        "message": message
                    }

                logger.warning("没有找到可导入的文档")
                return {
                    "success": True,
                    "ingested_count": 0,
                    "message": "没有找到可导入的文档"
                }
            
            # 添加元数据
            documents = loader.add_metadata(documents, category)
            
            # 分割文档
            splitter = MedicalTextSplitter()
            split_docs = splitter.split_documents(documents)
            
            # 存储到向量数据库
            doc_ids = self.rag_chain.vector_store.add_documents(split_docs)
            
            result = {
                "success": len(doc_ids) > 0 or failed_count == 0,
                "ingested_count": len(doc_ids),
                "message": self._build_result_message(len(doc_ids), 0, failed_count, failed_files)
            }
            
            logger.info(f"全量更新完成: {result}")
            return result
        except Exception as e:
            logger.error(f"全量更新失败: {e}")
            return {
                "success": False,
                "ingested_count": 0,
                "message": f"更新失败: {str(e)}"
            }
    
    def update_single_file(self, filepath: str, category: str = "general", force: bool = False) -> Dict:
        """
        更新单个文件
        
        Args:
            filepath: 文件路径
            category: 文档分类
            force: 是否强制更新（忽略MD5检查）
            
        Returns:
            更新结果
        """
        try:
            logger.info(f"更新单个文件: {filepath}, force: {force}")
            
            # 根据force参数决定是否使用MD5检查
            loader = MedicalDocumentLoader(enable_md5_check=not force)
            
            # 加载文件
            documents, is_new = loader.load_single_file(filepath)
            
            if not documents:
                return {
                    "success": False,
                    "ingested_count": 0,
                    "message": "文件加载失败或文件已存在（使用force=True强制更新）"
                }
            
            # 添加元数据
            documents = loader.add_metadata(documents, category)
            
            # 分割文档
            splitter = MedicalTextSplitter()
            split_docs = splitter.split_documents(documents)
            
            # 存储到向量数据库
            doc_ids = self.rag_chain.vector_store.add_documents(split_docs)
            
            result = {
                "success": True,
                "ingested_count": len(doc_ids),
                "is_new": is_new,
                "message": f"成功导入 {len(doc_ids)} 个文档块"
            }
            
            logger.info(f"单文件更新完成: {result}")
            return result
        except Exception as e:
            logger.error(f"单文件更新失败: {e}")
            return {
                "success": False,
                "ingested_count": 0,
                "message": f"更新失败: {str(e)}"
            }
