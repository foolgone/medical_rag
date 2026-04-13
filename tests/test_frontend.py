"""前端组件测试"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import AppConfig
from app.api_client import APIClient


def test_config():
    """测试配置类"""
    config = AppConfig()
    assert config.page_title == "医疗Agent问答系统"
    assert config.api_base_url == "http://localhost:8000/api/v1"
    assert config.query_url == "http://localhost:8000/api/v1/query"
    print(f"✅ 配置类测试通过")


def test_api_client():
    """测试API客户端"""
    config = AppConfig()
    client = APIClient(config)
    assert client.config == config
    print(f"✅ API客户端测试通过")


if __name__ == "__main__":
    print("=" * 50)
    print("开始测试前端组件")
    print("=" * 50)

    test_config()
    test_api_client()

    print("\n" + "=" * 50)
    print("前端组件测试完成！")
    print("=" * 50)
