"""
MD5校验工具模块
用于文档去重检查
"""
import hashlib
from pathlib import Path
from typing import Optional, Set
from loguru import logger


class MD5Checker:
    """MD5校验管理器"""
    
    def __init__(self, md5_file: str = "data/md5_records.txt"):
        """
        初始化MD5校验器
        
        Args:
            md5_file: MD5记录文件路径
        """
        self.md5_file = Path(md5_file)
        self.md5_records: Set[str] = set()
        self._load_md5_records()
        logger.info(f"MD5校验器初始化完成，已加载 {len(self.md5_records)} 条记录")
    
    def _load_md5_records(self):
        """加载已保存的MD5记录"""
        if self.md5_file.exists():
            try:
                with open(self.md5_file, 'r', encoding='utf-8') as f:
                    self.md5_records = set(line.strip() for line in f if line.strip())
                logger.debug(f"成功加载MD5记录: {len(self.md5_records)}条")
            except Exception as e:
                logger.error(f"加载MD5记录失败: {e}")
                self.md5_records = set()
    
    def _save_md5_record(self, md5_hash: str):
        """保存单条MD5记录到文件"""
        try:
            self.md5_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.md5_file, 'a', encoding='utf-8') as f:
                f.write(f"{md5_hash}\n")
            self.md5_records.add(md5_hash)
        except Exception as e:
            logger.error(f"保存MD5记录失败: {e}")
    
    @staticmethod
    def get_file_md5(file_path: str) -> str:
        """
        计算文件的MD5值
        
        Args:
            file_path: 文件路径
            
        Returns:
            MD5哈希值
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                # 分块读取，适合大文件
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件MD5失败 {file_path}: {e}")
            raise
    
    @staticmethod
    def get_string_md5(text: str) -> str:
        """
        计算字符串的MD5值
        
        Args:
            text: 输入字符串
            
        Returns:
            MD5哈希值
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def check_file_exists(self, file_path: str) -> bool:
        """
        检查文件是否已存在（通过MD5）
        
        Args:
            file_path: 文件路径
            
        Returns:
            True表示已存在，False表示不存在
        """
        try:
            md5_hash = self.get_file_md5(file_path)
            return md5_hash in self.md5_records
        except Exception as e:
            logger.error(f"检查文件MD5失败: {e}")
            return False
    
    def add_file_record(self, file_path: str) -> str:
        """
        添加文件MD5记录
        
        Args:
            file_path: 文件路径
            
        Returns:
            MD5哈希值
        """
        md5_hash = self.get_file_md5(file_path)
        self._save_md5_record(md5_hash)
        return md5_hash
    
    def remove_record(self, md5_hash: str) -> bool:
        """
        删除MD5记录
        
        Args:
            md5_hash: MD5哈希值
            
        Returns:
            是否删除成功
        """
        if md5_hash in self.md5_records:
            self.md5_records.remove(md5_hash)
            # 重写整个文件
            try:
                with open(self.md5_file, 'w', encoding='utf-8') as f:
                    for hash_value in self.md5_records:
                        f.write(f"{hash_value}\n")
                return True
            except Exception as e:
                logger.error(f"删除MD5记录失败: {e}")
                return False
        return False
