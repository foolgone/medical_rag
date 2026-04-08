"""
知识库更新服务模块
提供增量更新、全量更新等功能
"""
from typing import Dict, List
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
    
    def incremental_update(self, data_dir: str = None, category: str = "general") -> Dict:
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
            loader = MedicalDocumentLoader(data_dir=data_dir, enable_md5_check=True)
            
            if data_dir:
                loader.data_dir = Path(data_dir)
            
            # 加载文档（自动跳过已存在的）
            documents, success_count, skip_count = loader.load_directory()
            
            if not documents:
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
                "success": True,
                "ingested_count": len(doc_ids),
                "skipped_count": skip_count,
                "file_count": success_count,
                "message": f"成功导入 {len(doc_ids)} 个文档块，跳过 {skip_count} 个已存在文件"
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
    
    def full_update(self, data_dir: str = None, category: str = "general", clear_first: bool = False) -> Dict:
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
            loader = MedicalDocumentLoader(data_dir=data_dir, enable_md5_check=False)
            
            if data_dir:
                loader.data_dir = Path(data_dir)
            
            # 加载所有文档
            documents, _, _ = loader.load_directory()
            
            if not documents:
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
                "success": True,
                "ingested_count": len(doc_ids),
                "message": f"全量更新完成，导入 {len(doc_ids)} 个文档块"
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
