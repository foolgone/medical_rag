"""
医疗Agent - 基于LangGraph的Tool Calling Agent
"""
import json
from typing import Any, Dict, List

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from langchain_core.documents import Document

from rag.rag_chain import MedicalRAGChain
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

        # 4. 初始化RAG链，用于统一主链路检索和统计
        self.rag_chain = MedicalRAGChain()

        # 5. 定义系统提示词
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

        # 6. 创建ReAct Agent
        self.agent = create_agent(
            self.llm,
            self.tools,
            system_prompt=self.system_prompt,  # 添加系统提示
            checkpointer=self.checkpointer
        )

        logger.info("医疗Agent初始化完成")

    @staticmethod
    def _normalize_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标准化工具调用信息"""
        normalized = []
        for tool_call in tool_calls:
            normalized.append({
                "name": tool_call.get("name", "unknown"),
                "args": tool_call.get("args", {}) or {}
            })
        return normalized

    @staticmethod
    def _extract_text(content: Any) -> str:
        """将模型消息内容统一为字符串"""
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts = []
            for item in content:
                if not isinstance(item, dict):
                    continue

                if item.get("type") == "text" and item.get("text"):
                    parts.append(item["text"])
                elif item.get("text"):
                    parts.append(str(item["text"]))

            return "".join(parts).strip()

        return str(content or "").strip()

    def _extract_final_answer(self, messages: List[Any]) -> str:
        """从消息列表中回溯提取最后一条有效文本回答"""
        for msg in reversed(messages):
            content = getattr(msg, "content", "")
            text = self._extract_text(content)
            if text:
                return text
        return ""

    @staticmethod
    def _iter_tool_calls(payload: Any) -> List[Dict[str, Any]]:
        """从流式更新事件中递归提取工具调用"""
        tool_calls: List[Dict[str, Any]] = []

        if isinstance(payload, dict):
            for value in payload.values():
                tool_calls.extend(MedicalAgent._iter_tool_calls(value))
            return tool_calls

        if isinstance(payload, (list, tuple)):
            for item in payload:
                tool_calls.extend(MedicalAgent._iter_tool_calls(item))
            return tool_calls

        if hasattr(payload, "tool_calls") and getattr(payload, "tool_calls"):
            tool_calls.extend(MedicalAgent._normalize_tool_calls(getattr(payload, "tool_calls")))

        return tool_calls

    @staticmethod
    def _tool_call_key(tool_call: Dict[str, Any]) -> str:
        """生成工具调用去重键"""
        return json.dumps(
            {
                "name": tool_call.get("name"),
                "args": tool_call.get("args", {})
            },
            ensure_ascii=False,
            sort_keys=True
        )

    def _build_messages(self, question: str, docs: List[Document], category: str = None) -> List[Dict[str, str]]:
        """构建Agent输入消息"""
        messages: List[Dict[str, str]] = []

        if docs:
            context = self.rag_chain.retriever.format_context(docs)
            category_prompt = f"当前仅优先使用分类 `{category}` 的知识库结果。" if category else "请优先使用以下知识库结果。"
            messages.append({
                "role": "system",
                "content": (
                    "以下是当前问题预先检索到的知识库内容。\n"
                    f"{category_prompt}\n"
                    "如果以下内容足够，请直接基于这些资料回答；如果不足，请明确说明信息有限。\n\n"
                    f"{context}"
                )
            })

        messages.append({"role": "user", "content": question})
        return messages

    def _execute_query(
        self,
        question: str,
        thread_id: str = "default",
        k: int = None,
        category: str = None
    ) -> Dict[str, Any]:
        """执行统一问答主链路"""
        logger.info(f"Agent处理问题: {question[:50]}...")

        # 配置线程ID
        config = {"configurable": {"thread_id": thread_id}}
        filter_dict = self.rag_chain.build_filter_dict(category)

        try:
            docs = self.rag_chain.retriever.retrieve(
                query=question,
                k=k,
                filter_dict=filter_dict
            )

            # 调用Agent
            result = self.agent.invoke(
                {"messages": self._build_messages(question, docs, category)},
                config=config
            )

            # 回溯提取最后一条真正的文本回答，避免把工具调用块当正文
            answer = self._extract_final_answer(result["messages"])

            # 提取工具调用信息
            tool_calls = []
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_calls.extend(msg.tool_calls)

            normalized_tool_calls = self._normalize_tool_calls(tool_calls)
            sources = self.rag_chain.serialize_sources(docs)

            logger.info(f"Agent回答完成，调用工具数: {len(tool_calls)}")

            return {
                "question": question,
                "answer": answer,
                "session_id": thread_id,
                "sources": sources,
                "tool_calls": normalized_tool_calls,
                "tool_calls_count": len(normalized_tool_calls),
                "debug_info": {
                    "requested_k": k,
                    "applied_category": category,
                    "retrieval_count": len(sources),
                    "used_chat_mode": len(sources) == 0
                }
            }
        except Exception as e:
            logger.error(f"Agent执行失败: {e}")
            return {
                "question": question,
                "answer": f"⚠️ 处理失败: {str(e)}",
                "session_id": thread_id,
                "sources": [],
                "tool_calls": [],
                "tool_calls_count": 0,
                "debug_info": {
                    "requested_k": k,
                    "applied_category": category,
                    "retrieval_count": 0,
                    "used_chat_mode": True
                }
            }

    def query(
        self,
        question: str,
        thread_id: str = "default",
        k: int = None,
        category: str = None
    ) -> Dict[str, Any]:
        """使用Agent回答问题"""
        return self._execute_query(question, thread_id=thread_id, k=k, category=category)

    def stream_query(
        self,
        question: str,
        thread_id: str = "default",
        k: int = None,
        category: str = None
    ):
        """
        流式查询（输出标准化事件）
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            filter_dict = self.rag_chain.build_filter_dict(category)
            docs = self.rag_chain.retriever.retrieve(
                query=question,
                k=k,
                filter_dict=filter_dict
            )
            sources = self.rag_chain.serialize_sources(docs)
            messages = self._build_messages(question, docs, category)
            answer_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []
            seen_tool_calls = set()

            yield {
                "type": "start",
                "message": "Agent开始处理",
                "session_id": thread_id
            }

            if sources:
                yield {
                    "type": "retrieval",
                    "sources": sources
                }

            for event in self.agent.stream(
                {"messages": messages},
                config=config,
                stream_mode=["messages", "updates"]
            ):
                if not isinstance(event, tuple):
                    continue

                if len(event) == 2:
                    mode, data = event
                elif len(event) == 3:
                    _, mode, data = event
                else:
                    continue

                if mode == "messages":
                    message_chunk, _metadata = data
                    text = self._extract_text(getattr(message_chunk, "content", ""))
                    if text:
                        answer_parts.append(text)
                        yield {
                            "type": "content",
                            "content": text
                        }

                elif mode == "updates":
                    for tool_call in self._iter_tool_calls(data):
                        key = self._tool_call_key(tool_call)
                        if key in seen_tool_calls:
                            continue
                        seen_tool_calls.add(key)
                        tool_calls.append(tool_call)
                        yield {
                            "type": "tool_call",
                            "tools": [tool_call]
                        }

            answer = "".join(answer_parts).strip()

            yield {
                "type": "end",
                "question": question,
                "answer": answer,
                "session_id": thread_id,
                "sources": sources,
                "tool_calls": tool_calls,
                "tool_calls_count": len(tool_calls),
                "debug_info": {
                    "requested_k": k,
                    "applied_category": category,
                    "retrieval_count": len(sources),
                    "used_chat_mode": len(sources) == 0
                }
            }
        except Exception as e:
            logger.error(f"流式查询失败: {e}")
            yield {"type": "error", "error": str(e)}


# 全局Agent实例
medical_agent = MedicalAgent()
