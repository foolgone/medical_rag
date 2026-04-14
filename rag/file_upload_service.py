"""
文件上传服务模块
处理文件上传、验证和存储
"""
import os
import re
import shutil
from hashlib import md5
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import UploadFile, HTTPException
from loguru import logger
from rag.md5_checker import MD5Checker
from database.connection import get_db_session
from database.models import KnowledgeBaseFile


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

    @staticmethod
    def normalize_logical_name(filename: str) -> str:
        """将物理文件名归一为逻辑文件名，忽略上传冲突追加的数字后缀。"""
        path = Path(filename or "uploaded_file.txt")
        stem = re.sub(r"_\d+$", "", path.stem)
        suffix = path.suffix.lower() or ".txt"
        return f"{stem}{suffix}"

    @classmethod
    def build_source_id(cls, filename: str, category: str = "general") -> str:
        """基于逻辑文件名和分类构建稳定 source_id。"""
        logical_name = cls.normalize_logical_name(filename).lower()
        source_key = f"{category.lower()}::{logical_name}"
        return f"src_{md5(source_key.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """计算文件哈希。"""
        return MD5Checker.get_file_md5(file_path)

    def build_file_identity(
        self,
        file_path: Path,
        category: str,
        original_filename: Optional[str] = None
    ) -> Dict[str, str]:
        """生成文件身份信息。"""
        logical_name = self.normalize_logical_name(original_filename or file_path.name)
        return {
            "source_id": self.build_source_id(logical_name, category),
            "logical_name": logical_name,
            "file_hash": self.compute_file_hash(str(file_path)),
            "source_type": file_path.suffix.lower().lstrip(".") or "unknown",
        }

    def _upsert_uploaded_file_record(
        self,
        file_path: Path,
        category: str,
        original_filename: Optional[str] = None
    ) -> Dict[str, object]:
        """在治理表中登记上传文件。"""
        identity = self.build_file_identity(file_path, category, original_filename)
        with get_db_session() as db:
            existing = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.filepath == str(file_path)) \
                .first()

            if existing:
                existing.filename = file_path.name
                existing.category = category
                existing.logical_name = identity["logical_name"]
                existing.source_type = identity["source_type"]
                existing.file_hash = identity["file_hash"]
                existing.status = existing.status or "uploaded"
                existing.error_message = None
                db.flush()
                version = existing.version
                record_id = existing.id
            else:
                latest = db.query(KnowledgeBaseFile) \
                    .filter(KnowledgeBaseFile.source_id == identity["source_id"]) \
                    .order_by(KnowledgeBaseFile.version.desc()) \
                    .first()
                version = (latest.version + 1) if latest else 1

                record = KnowledgeBaseFile(
                    source_id=identity["source_id"],
                    filename=file_path.name,
                    filepath=str(file_path),
                    logical_name=identity["logical_name"],
                    category=category,
                    source_type=identity["source_type"],
                    file_hash=identity["file_hash"],
                    version=version,
                    status="uploaded",
                    is_current=False,
                )
                db.add(record)
                db.flush()
                record_id = record.id

        identity["version"] = version
        identity["file_record_id"] = record_id
        return identity
    
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
            try:
                identity = self._upsert_uploaded_file_record(
                    file_path=file_path,
                    category=category,
                    original_filename=original_filename,
                )
            except Exception as governance_error:
                logger.warning(f"登记知识库文件治理信息失败，回退到本地身份信息: {governance_error}")
                identity = self.build_file_identity(file_path=file_path, category=category, original_filename=original_filename)
                identity["version"] = 1
                identity["file_record_id"] = None
            
            return {
                "filename": file_path.name,
                "filepath": str(file_path),
                "category": category,
                "size": file_path.stat().st_size,
                "success": True,
                "source_id": identity["source_id"],
                "file_hash": identity["file_hash"],
                "version": identity["version"],
                "status": "uploaded",
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
                try:
                    with get_db_session() as db:
                        record = db.query(KnowledgeBaseFile) \
                            .filter(KnowledgeBaseFile.filepath == str(file_path)) \
                            .first()
                        if record:
                            record.status = "deleted"
                            record.is_current = False
                except Exception as db_error:
                    logger.warning(f"更新文件治理状态失败: {db_error}")
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
        files: List[Dict] = []
        seen_paths = set()
        try:
            with get_db_session() as db:
                query = db.query(KnowledgeBaseFile)
                if category:
                    query = query.filter(KnowledgeBaseFile.category == category)
                registry_rows = query \
                    .filter(KnowledgeBaseFile.status != "deleted") \
                    .order_by(
                        KnowledgeBaseFile.updated_at.desc(),
                        KnowledgeBaseFile.version.desc(),
                        KnowledgeBaseFile.id.desc(),
                    ) \
                    .all()

                for row in registry_rows:
                    seen_paths.add(row.filepath)
                    file_path = Path(row.filepath)
                    size = file_path.stat().st_size if file_path.exists() else 0
                    upload_time = row.uploaded_at or row.updated_at or row.created_at
                    files.append({
                        "filename": row.filename,
                        "category": row.category,
                        "size": size,
                        "path": row.filepath,
                        "filepath": row.filepath,
                        "upload_time": upload_time.strftime("%Y-%m-%d %H:%M:%S") if upload_time else None,
                        "status": row.status,
                        "source_id": row.source_id,
                        "file_hash": row.file_hash,
                        "version": row.version,
                        "is_current": row.is_current,
                    })
        except Exception as e:
            logger.warning(f"读取知识库文件治理信息失败，回退到文件系统列表: {e}")

        if category:
            search_dirs = [self.upload_dir / category]
        else:
            search_dirs = [self.upload_dir]

        md5_checker = MD5Checker()
        for search_dir in search_dirs:
            if search_dir.exists():
                for file_path in search_dir.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in self.ALLOWED_EXTENSIONS:
                        normalized_path = str(file_path)
                        if normalized_path in seen_paths:
                            continue
                        files.append({
                            "filename": file_path.name,
                            "category": file_path.parent.name,
                            "size": file_path.stat().st_size,
                            "path": normalized_path,
                            "filepath": normalized_path,
                            "upload_time": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "active" if md5_checker.check_file_exists(normalized_path) else "uploaded",
                            "source_id": self.build_source_id(file_path.name, file_path.parent.name),
                            "file_hash": self.compute_file_hash(normalized_path),
                            "version": None,
                            "is_current": None,
                        })

        return files

    def get_version_history(self, source_id: str) -> List[KnowledgeBaseFile]:
        """读取指定逻辑文件的所有版本历史。"""
        with get_db_session() as db:
            return db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.source_id == source_id) \
                .order_by(KnowledgeBaseFile.version.desc(), KnowledgeBaseFile.updated_at.desc()) \
                .all()
