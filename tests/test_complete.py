"""完整流程测试"""
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"


def test_complete_workflow():
    """测试完整工作流程"""
    print("\n1. 测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("   ✅ 后端服务正常")

    print("\n2. 测试工具调用（BMI计算）...")
    payload = {
        "question": "我身高180cm，体重80kg，请计算我的BMI",
        "session_id": "workflow_test",
        "k": 3
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "22.2" in data["answer"] or "22.22" in data["answer"]
    print(f"   ✅ BMI计算正确: {data['answer'][:100]}")
    print(f"   调用工具数: {data.get('tool_calls_count', 0)}")

    print("\n3. 测试症状分析...")
    payload = {
        "question": "我头痛、发热已经3天了，可能是什么病？",
        "session_id": "workflow_test",
        "k": 3
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    print(f"   ✅ 症状分析完成: {data['answer'][:100]}...")

    print("\n4. 测试科室推荐...")
    payload = {
        "question": "胸痛应该挂什么科？",
        "session_id": "workflow_test",
        "k": 3
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "心内" in data["answer"] or "急诊" in data["answer"]
    print(f"   ✅ 科室推荐完成: {data['answer'][:100]}...")

    print("\n5. 测试流式输出...")
    payload = {
        "question": "高血压应该注意什么？",
        "session_id": "workflow_test",
        "k": 3
    }
    response = requests.post(
        f"{BASE_URL}/query-stream",
        json=payload,
        stream=True,
        headers={"Accept": "text/event-stream"}
    )
    assert response.status_code == 200

    content = ""
    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get("type") == "content":
                    content += data.get("content", "")
            except:
                pass

    assert len(content) > 0
    print(f"   ✅ 流式输出完成，共{len(content)}字符")


if __name__ == "__main__":
    print("=" * 60)
    print("开始完整流程测试")
    print("=" * 60)

    try:
        test_complete_workflow()

        print("\n" + "=" * 60)
        print("🎉 所有测试通过！系统运行正常！")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务")
        print("请先执行: python main.py")
    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")
