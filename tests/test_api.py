"""API路由测试"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def test_health_check():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print(f"✅ 健康检查测试通过")


def test_query_api():
    """测试问答API"""
    payload = {
        "question": "感冒应该吃什么药？",
        "session_id": "test_session",
        "k": 3
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    print(f"✅ 问答API测试通过")
    print(f"回答: {data['answer'][:100]}...")


def test_stats_api():
    """测试统计API"""
    response = requests.get(f"{BASE_URL}/stats")
    assert response.status_code == 200
    data = response.json()
    assert "collection_name" in data
    print(f"✅ 统计API测试通过")


def test_files_api():
    """测试文件列表API"""
    response = requests.get(f"{BASE_URL}/files")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert "total" in data
    print(f"✅ 文件列表API测试通过，共{data['total']}个文件")


if __name__ == "__main__":
    print("=" * 50)
    print("开始测试API接口")
    print("=" * 50)

    try:
        test_health_check()
        test_stats_api()
        test_files_api()
        test_query_api()

        print("\n" + "=" * 50)
        print("所有API测试完成！")
        print("=" * 50)
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请先启动: python main.py")
