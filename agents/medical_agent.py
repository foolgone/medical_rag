"""
医疗Agent - 基于LangGraph的Tool Calling Agent
"""
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from typing import Optional, Dict, Any
from loguru import logger

from tools.medical_tools import medical_tools
from tools.rag_tool import search_medical_knowledge, get_disease_info


class MedicalAgent:
    """医疗智能助手Agent"""

    def __init__(self, model_name: str = "qwen2.5:7b", temperature: float = 0.7):
        """
        初始化Agent

        Args:
            model_name: Ollama模型名称
            temperature: 温度参数（建议0.7保持一定创造性）
        """
        logger.info("初始化医疗Agent...")

        # 1. 初始化工具集
        self.tools = medical_tools + [search_medical_knowledge, get_disease_info]
        logger.info(f"已加载 {len(self.tools)} 个工具")

        # 2. 初始化LLM
        self.llm = ChatOllama(
            model=model_name,
            temperature=temperature
        )

        # 3. 创建记忆检查点
        self.checkpointer = MemorySaver()

        # 4. 定义系统提示词
        self.system_prompt = """你是一个专业的医疗智能助手，具备以下能力：

1. **症状分析** - 分析患者症状并提供初步建议
2. **健康计算** - 计算BMI等健康指标
3. **血压评估** - 根据血压值判断分级
4. **科室推荐** - 根据症状推荐就诊科室
5. **知识检索** - 从医学知识库检索相关信息
6. **疾病查询** - 查询特定疾病的详细信息

工作原则：
- 回答要专业、准确、易懂
- 涉及诊断或用药时，提醒用户咨询专业医生
- 使用工具获取准确信息，不要编造数据
- 承认知识局限性，不过度自信
- 必要时建议用户就医

请根据用户问题，合理选择和使用工具。"""

        # 5. 创建ReAct Agent
        self.agent = create_agent(
            self.llm,
            self.tools,
            system_prompt=self.system_prompt,  # 添加系统提示
            checkpointer=self.checkpointer
        )

        logger.info("医疗Agent初始化完成")

    def query(
            self,
            question: str,
            thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        使用Agent回答问题

        Args:
            question: 用户问题
            thread_id: 会话ID（用于记忆隔离）

        Returns:
            包含回答和中间过程的字典
        """
        logger.info(f"Agent处理问题: {question[:50]}...")

        # 配置线程ID
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # 调用Agent
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": question}]},
                config=config
            )

            # 提取最终回答
            answer = result["messages"][-1].content

            # 提取工具调用信息
            tool_calls = []
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_calls.extend(msg.tool_calls)

            logger.info(f"Agent回答完成，调用工具数: {len(tool_calls)}")

            return {
                "question": question,
                "answer": answer,
                "thread_id": thread_id,
                "tool_calls_count": len(tool_calls)
            }
        except Exception as e:
            logger.error(f"Agent执行失败: {e}")
            return {
                "question": question,
                "answer": f"⚠️ 处理失败: {str(e)}",
                "thread_id": thread_id,
                "tool_calls_count": 0
            }

    def stream_query(
            self,
            question: str,
            thread_id: str = "default"
    ):
        """
        流式查询（实时输出思考过程）

        Args:
            question: 用户问题
            thread_id: 会话ID

        Yields:
            事件流数据
        """
        config = {"configurable": {"thread_id": thread_id}}

        try:
            for event in self.agent.stream(
                    {"messages": [{"role": "user", "content": question}]},
                    config=config,
                    stream_mode="values"
            ):
                yield event
        except Exception as e:
            logger.error(f"流式查询失败: {e}")
            yield {"error": str(e)}


# 全局Agent实例
medical_agent = MedicalAgent()
