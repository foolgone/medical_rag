"""
文件上传服务模块
处理文件上传、验证和存储
"""
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict
from fastapi import UploadFile, HTTPException
from loguru import logger


class FileUploadService:
    """文件上传服务"""
    
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    
    def __init__(self, upload_dir: str = "data/medical_docs"):
        """
        初始化文件上传服务
        
        Args:
            upload_dir: 上传文件存储目录
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"文件上传服务初始化完成，目录: {self.upload_dir}")
    
    def validate_file(self, file: UploadFile) -> None:
        """
        验证上传文件
        
        Args:
            file: 上传的文件对象
            
        Raises:
            HTTPException: 验证失败时抛出
        """
        # 检查文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}，支持的格式: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # 检查文件大小
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置指针
        
        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大: {file_size / 1024 / 1024:.2f}MB，最大允许: {self.MAX_FILE_SIZE / 1024 / 1024}MB"
            )

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """清洗Windows不允许的文件名字符，保留扩展名。"""
        original_name = Path(filename or "uploaded_file")
        stem = re.sub(cls.INVALID_FILENAME_CHARS, "_", original_name.stem).strip(" .")
        suffix = re.sub(cls.INVALID_FILENAME_CHARS, "_", original_name.suffix)

        if not stem:
            stem = "uploaded_file"
        if not suffix:
            suffix = ".txt"

        sanitized = f"{stem}{suffix}"
        if sanitized != (filename or ""):
            logger.warning(f"文件名包含非法字符，已重命名: {filename} -> {sanitized}")
        return sanitized
    
    async def save_uploaded_file(self, file: UploadFile, category: str = "general") -> Dict:
        """
        保存上传的文件
        
        Args:
            file: 上传的文件对象
            category: 文档分类
            
        Returns:
            文件信息字典
        """
        try:
            # 验证文件
            self.validate_file(file)
            
            # 创建分类子目录
            category_dir = self.upload_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成安全的文件名（保留原始扩展名）
            original_filename = file.filename
            safe_filename = self.sanitize_filename(original_filename)
            file_ext = Path(safe_filename).suffix
            
            file_path = category_dir / safe_filename
            
            # 如果文件已存在，添加数字后缀
            counter = 1
            while file_path.exists():
                file_path = category_dir / f"{Path(safe_filename).stem}_{counter}{file_ext}"
                counter += 1
            
            # 保存文件
            with open(file_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"文件上传成功: {file_path.name}, 大小: {file_path.stat().st_size / 1024:.2f}KB")
            
            return {
                "filename": file_path.name,
                "filepath": str(file_path),
                "category": category,
                "size": file_path.stat().st_size,
                "success": True
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    async def save_multiple_files(self, files: List[UploadFile], category: str = "general") -> List[Dict]:
        """
        批量保存上传的文件
        
        Args:
            files: 上传的文件列表
            category: 文档分类
            
        Returns:
            文件信息列表
        """
        results = []
        for file in files:
            try:
                result = await self.save_uploaded_file(file, category)
                results.append(result)
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def delete_file(self, filename: str, category: str = "general") -> bool:
        """
        删除已上传的文件
        
        Args:
            filename: 文件名
            category: 文档分类
            
        Returns:
            是否删除成功
        """
        try:
            file_path = self.upload_dir / category / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"文件删除成功: {filename}")
                return True
            else:
                logger.warning(f"文件不存在: {filename}")
                return False
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False
    
    def list_uploaded_files(self, category: str = None) -> List[Dict]:
        """
        列出已上传的文件
        
        Args:
            category: 文档分类（可选）
            
        Returns:
            文件信息列表
        """
        files = []
        
        if category:
            search_dirs = [self.upload_dir / category]
        else:
            search_dirs = [self.upload_dir]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for file_path in search_dir.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in self.ALLOWED_EXTENSIONS:
                        files.append({
                            "filename": file_path.name,
                            "category": file_path.parent.name,
                            "size": file_path.stat().st_size,
                            "path": str(file_path)
                        })
        
        return files
