"""API客户端封装"""
import requests
import json
from typing import Dict, List, Optional, Generator
from loguru import logger
from app.config import AppConfig

class APIClient:
    """API客户端"""

    def __init__(self, config: AppConfig):
        self.config = config

    def query(self, question: str, session_id: str, top_k: int = 5) -> Dict:
        """标准问答"""
        try:
            response = requests.post(
                self.config.query_url,
                json={"question": question, "session_id": session_id, "k": top_k},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"查询失败: {e}")
            raise

    def query_stream(self, question: str, session_id: str, top_k: int = 5) -> Generator:
        """流式问答"""
        try:
            response = requests.post(
                self.config.query_stream_url,
                json={"question": question, "session_id": session_id, "k": top_k},
                stream=True,
                timeout=self.config.timeout,
                headers={"Accept": "text/event-stream"}
            )
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        yield json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"流式查询失败: {e}")
            raise

    def upload_file(self, file, category: str = "general") -> Dict:
        """上传文件"""
        try:
            files = {'file': (file.name, file.getvalue(), file.type)}
            response = requests.post(
                self.config.upload_url,
                files=files,
                data={'category': category}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise

    def upload_batch(self, files_data: List, category: str = "general") -> Dict:
        """批量上传"""
        try:
            response = requests.post(
                self.config.upload_batch_url,
                files=files_data,
                data={'category': category}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"批量上传失败: {e}")
            raise

    def ingest_file(self, filepath: str, category: str = "general") -> Dict:
        """导入文件到知识库"""
        try:
            response = requests.post(
                self.config.ingest_file_url,
                params={'filepath': filepath, 'category': category}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"文件导入失败: {e}")
            raise

    def get_stats(self) -> Dict:
        """获取统计信息"""
        try:
            response = requests.get(self.config.stats_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            raise

    def list_files(self, category: str = None) -> Dict:
        """获取文件列表"""
        try:
            params = {'category': category} if category else {}
            response = requests.get(self.config.files_url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取文件列表失败: {e}")
            raise

    def incremental_update(self) -> Dict:
        """增量更新"""
        try:
            response = requests.post(self.config.update_incremental_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"增量更新失败: {e}")
            raise

    def full_update(self) -> Dict:
        """全量更新"""
        try:
            response = requests.post(self.config.update_full_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"全量更新失败: {e}")
            raise
