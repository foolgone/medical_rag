"""前端组件测试"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import AppConfig
from app.api_client import APIClient
from app.components.knowledge_base.file_item import _highlight_preview_text, _load_file_preview


def test_config():
    """测试配置类"""
    config = AppConfig()
    assert config.page_title == "医疗Agent问答系统"
    assert config.api_base_url == "http://localhost:8000/api/v1"
    assert config.query_url == "http://localhost:8000/api/v1/query"
    assert config.delete_by_rule_url == "http://localhost:8000/api/v1/documents/delete-by-rule"
    assert config.rollback_document_url == "http://localhost:8000/api/v1/documents/rollback"
    assert config.document_versions_url == "http://localhost:8000/api/v1/documents"
    assert config.ingest_jobs_url == "http://localhost:8000/api/v1/ingest-jobs"
    print(f"✅ 配置类测试通过")


def test_api_client():
    """测试API客户端"""
    config = AppConfig()
    client = APIClient(config)
    assert client.config == config
    print(f"✅ API客户端测试通过")


def test_api_client_governance_methods():
    """测试知识库治理相关客户端方法"""
    config = AppConfig()
    client = APIClient(config)

    with patch("app.api_client.requests.post") as mock_post:
        delete_response = MagicMock()
        delete_response.json.return_value = {"success": True, "message": "ok"}
        delete_response.raise_for_status.return_value = None
        mock_post.return_value = delete_response

        result = client.delete_by_rule(source_id="src_123", version=2)
        assert result["success"] is True
        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {"source_id": "src_123", "version": 2}

    with patch("app.api_client.requests.post") as mock_post:
        rollback_response = MagicMock()
        rollback_response.json.return_value = {"success": True, "version": 2}
        rollback_response.raise_for_status.return_value = None
        mock_post.return_value = rollback_response

        result = client.rollback_document("src_123", 2)
        assert result["version"] == 2
        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {"source_id": "src_123", "target_version": 2}

    with patch("app.api_client.requests.get") as mock_get:
        versions_response = MagicMock()
        versions_response.json.return_value = {"source_id": "src_123", "total": 2, "versions": []}
        versions_response.raise_for_status.return_value = None
        mock_get.return_value = versions_response

        result = client.get_document_versions("src_123")
        assert result["total"] == 2
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == config.timeout

    with patch("app.api_client.requests.get") as mock_get:
        jobs_response = MagicMock()
        jobs_response.json.return_value = {"total": 1, "jobs": [{"status": "failed"}]}
        jobs_response.raise_for_status.return_value = None
        mock_get.return_value = jobs_response

        result = client.get_ingest_jobs(status="failed", limit=10)
        assert result["total"] == 1
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"limit": 10, "status": "failed"}

    print("✅ 知识库治理客户端测试通过")


def test_load_file_preview_for_txt():
    """TXT 文件预览应能读取文本内容。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "preview.txt"
        file_path.write_text("这是一个预览测试文件。", encoding="utf-8")

        result = _load_file_preview(str(file_path))

    assert result["success"] is True
    assert "预览测试文件" in result["content"]
    assert result["summary"] == "文本文件预览"
    print("✅ 文件预览测试通过")


def test_highlight_preview_text_marks_keyword():
    """关键词高亮应在预览 HTML 中加入 mark 标签。"""
    rendered = _highlight_preview_text("感冒时多喝水，多休息。", "喝水")
    assert "<mark" in rendered
    assert "喝水" in rendered
    print("✅ 关键词高亮测试通过")


if __name__ == "__main__":
    print("=" * 50)
    print("开始测试前端组件")
    print("=" * 50)

    test_config()
    test_api_client()
    test_api_client_governance_methods()
    test_load_file_preview_for_txt()
    test_highlight_preview_text_marks_keyword()

    print("\n" + "=" * 50)
    print("前端组件测试完成！")
    print("=" * 50)
