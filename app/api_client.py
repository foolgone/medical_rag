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

    def query(
        self,
        question: str,
        session_id: str,
        top_k: int = 5,
        category: Optional[str] = None,
        mode: str = "agent"
    ) -> Dict:
        """标准问答"""
        try:
            payload = {"question": question, "session_id": session_id, "k": top_k}
            if category and category != "all":
                payload["category"] = category

            response = requests.post(
                self.config.query_rag_url if mode == "rag" else self.config.query_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"查询失败: {e}")
            raise

    def query_stream(
        self,
        question: str,
        session_id: str,
        top_k: int = 5,
        category: Optional[str] = None,
        mode: str = "agent"
    ) -> Generator:
        """流式问答"""
        try:
            payload = {"question": question, "session_id": session_id, "k": top_k}
            if category and category != "all":
                payload["category"] = category

            response = requests.post(
                self.config.query_stream_rag_url if mode == "rag" else self.config.query_stream_url,
                json=payload,
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

    def delete_by_rule(
        self,
        source_id: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Dict:
        """按文件生命周期维度删除知识库内容。"""
        try:
            payload = {}
            if source_id:
                payload["source_id"] = source_id
            if category:
                payload["category"] = category
            if source:
                payload["source"] = source
            if version is not None:
                payload["version"] = version

            response = requests.post(
                self.config.delete_by_rule_url,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"治理删除失败: {e}")
            raise

    def rollback_document(self, source_id: str, target_version: int) -> Dict:
        """回滚到指定文件版本。"""
        try:
            response = requests.post(
                self.config.rollback_document_url,
                json={"source_id": source_id, "target_version": target_version},
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"版本回滚失败: {e}")
            raise

    def get_document_versions(self, source_id: str) -> Dict:
        """查询指定逻辑文件的版本历史。"""
        try:
            response = requests.get(
                f"{self.config.document_versions_url}/{source_id}/versions",
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取文件版本历史失败: {e}")
            raise

    def get_ingest_jobs(self, status: Optional[str] = None, limit: int = 20) -> Dict:
        """查询知识库导入任务日志。"""
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status

            response = requests.get(
                self.config.ingest_jobs_url,
                params=params,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取知识库导入任务失败: {e}")
            raise
