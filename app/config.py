"""应用配置"""
from dataclasses import dataclass

@dataclass
class AppConfig:
    """应用配置类"""
    api_base_url: str = "http://localhost:8000/api/v1"
    page_title: str = "医疗Agent问答系统"
    page_icon: str = "🏥"
    default_top_k: int = 5
    timeout: int = 120

    @property
    def query_url(self) -> str:
        return f"{self.api_base_url}/query"

    @property
    def query_stream_url(self) -> str:
        return f"{self.api_base_url}/query-stream"

    @property
    def upload_url(self) -> str:
        return f"{self.api_base_url}/upload"

    @property
    def upload_batch_url(self) -> str:
        return f"{self.api_base_url}/upload/batch"

    @property
    def ingest_file_url(self) -> str:
        return f"{self.api_base_url}/ingest-file"

    @property
    def stats_url(self) -> str:
        return f"{self.api_base_url}/stats"

    @property
    def files_url(self) -> str:
        return f"{self.api_base_url}/files"

    @property
    def update_incremental_url(self) -> str:
        return f"{self.api_base_url}/update/incremental"

    @property
    def update_full_url(self) -> str:
        return f"{self.api_base_url}/update/full"
