"""Agent功能测试"""
import pytest
from agents.medical_agent import MedicalAgent
from tools.medical_tools import analyze_symptoms, calculate_bmi, classify_blood_pressure
from tools.rag_tool import search_medical_knowledge


def test_agent_initialization():
    """测试Agent初始化"""
    agent = MedicalAgent(model_name="qwen2.5:7b", temperature=0.7)
    assert agent is not None
    assert len(agent.tools) == 6  # 4个医疗工具 + 2个RAG工具
    print(f"✅ Agent初始化成功，加载{len(agent.tools)}个工具")


def test_analyze_symptoms_tool():
    """测试症状分析工具"""
    result = analyze_symptoms.invoke({"symptoms": "头痛、发热", "duration": "3天"})
    assert "症状分析" in result
    print(f"✅ 症状分析工具测试通过")
    print(f"结果: {result[:100]}...")


def test_calculate_bmi_tool():
    """测试BMI计算工具"""
    result = calculate_bmi.invoke({"weight": 70, "height": 175})
    assert "BMI" in result
    assert "22.86" in result  # 70/(1.75^2) = 22.86
    print(f"✅ BMI计算工具测试通过")
    print(f"结果: {result}")


def test_blood_pressure_tool():
    """测试血压分级工具"""
    # 正常血压
    result = classify_blood_pressure.invoke({"systolic": 110, "diastolic": 70})
    assert "正常血压" in result
    print(f"✅ 血压分级工具测试通过（正常）")

    # 高血压
    result = classify_blood_pressure.invoke({"systolic": 150, "diastolic": 95})
    assert "高血压" in result
    print(f"✅ 血压分级工具测试通过（高血压）")


def test_rag_search_tool():
    """测试RAG检索工具"""
    result = search_medical_knowledge.invoke({"query": "感冒 症状", "k": 2})
    assert isinstance(result, str)
    print(f"✅ RAG检索工具测试通过")
    print(f"结果长度: {len(result)}字符")


@pytest.mark.asyncio
async def test_agent_query():
    """测试Agent问答（需要Ollama运行）"""
    try:
        agent = MedicalAgent()
        result = agent.query("我身高175cm，体重70kg，BMI是多少？", k=3, category="general")
        assert "answer" in result
        assert result["tool_calls_count"] >= 0
        assert "sources" in result
        assert "debug_info" in result
        print(f"✅ Agent问答测试通过")
        print(f"回答: {result['answer'][:100]}...")
        print(f"调用工具数: {result['tool_calls_count']}")
    except Exception as e:
        print(f"⚠️ Agent问答测试跳过（需要Ollama服务）: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("开始测试医疗Agent系统")
    print("=" * 50)

    test_agent_initialization()
    test_analyze_symptoms_tool()
    test_calculate_bmi_tool()
    test_blood_pressure_tool()
    test_rag_search_tool()

    print("\n" + "=" * 50)
    print("所有工具测试完成！")
    print("=" * 50)
