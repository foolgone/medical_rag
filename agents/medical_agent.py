"""
医疗Agent - 基于LangGraph的Tool Calling Agent
"""
import json
import uuid
from typing import Any, Dict, List

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from langchain_core.documents import Document

from memory.conversation_memory import ConversationMemory
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

        # 5. 初始化数据库记忆，用于跨轮次持久上下文
        self.memory = ConversationMemory(window_size=5)

        # 6. 定义系统提示词
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

        # 7. 创建ReAct Agent
        self.agent = create_agent(
            self.llm,
            self.tools,
            system_prompt=self.system_prompt,  # 添加系统提示
            checkpointer=self.checkpointer
        )

        logger.info("医疗Agent初始化完成")

    @staticmethod
    def _build_runtime_thread_id(session_id: str) -> str:
        """
        构建单次调用的运行线程ID

        使用数据库记忆承担跨轮次上下文，MemorySaver 仅保留单次运行内部状态，
        避免同一历史在数据库和 LangGraph 检查点中重复累积。
        """
        return f"{session_id}:{uuid.uuid4().hex}"

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

    def _get_memory_bundle(self, session_id: str, question: str) -> Dict[str, Any]:
        """获取当前会话的分层记忆包。"""
        if not session_id:
            return {
                "short_term_messages": [],
                "fact_memory": [],
                "summary_memory": "",
                "debug_info": {
                    "memory_message_count": 0,
                    "fact_count": 0,
                    "summary_applied": False,
                }
            }

        if hasattr(self.memory, "build_memory_bundle"):
            bundle = self.memory.build_memory_bundle(session_id, query=question)
        else:
            messages = self.memory.get_short_term_memory(session_id)
            bundle = {
                "short_term_messages": messages,
                "fact_memory": [],
                "summary_memory": "",
                "debug_info": {
                    "memory_message_count": len(messages),
                    "fact_count": 0,
                    "summary_applied": False,
                }
            }

        logger.debug(
            "加载数据库分层记忆，session_id: {}, 短期消息: {}, 事实数: {}, 摘要: {}",
            session_id,
            len(bundle.get("short_term_messages", [])),
            len(bundle.get("fact_memory", [])),
            bool(bundle.get("summary_memory")),
        )
        return bundle

    def _build_memory_reasoning_steps(
        self,
        sources: List[Dict[str, Any]],
        category: str = None,
        memory_bundle: Dict[str, Any] = None
    ) -> List[str]:
        """构建可落库的推理摘要"""
        memory_debug = (memory_bundle or {}).get("debug_info", {})
        reasoning_steps = [
            f"memory_messages={memory_debug.get('memory_message_count', 0)}",
            f"fact_memory={memory_debug.get('fact_count', 0)}",
            f"summary_applied={memory_debug.get('summary_applied', False)}",
            f"retrieval_count={len(sources)}",
            f"category={category or 'all'}",
        ]

        if sources:
            reasoning_steps.append(
                "retrieval_sources=" + ", ".join(source.get("source", "未知") for source in sources[:3])
            )

        return reasoning_steps

    def _build_memory_metadata(
        self,
        sources: List[Dict[str, Any]],
        category: str = None,
        memory_bundle: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """构建结构化记忆元数据"""
        memory_debug = (memory_bundle or {}).get("debug_info", {})
        return {
            "memory_message_count": memory_debug.get("memory_message_count", 0),
            "fact_memory_count": memory_debug.get("fact_count", 0),
            "summary_memory_applied": memory_debug.get("summary_applied", False),
            "retrieval_count": len(sources),
            "category": category or "all",
            "sources": [source.get("source", "未知") for source in sources[:5]],
        }

    def _save_memory_interaction(
        self,
        session_id: str,
        question: str,
        answer: str,
        tool_calls: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        category: str = None,
        memory_bundle: Dict[str, Any] = None
    ) -> None:
        """将 Agent 本轮交互写入数据库记忆"""
        if not session_id:
            return

        saved = self.memory.save_agent_interaction(
            session_id=session_id,
            question=question,
            answer=answer,
            tools_used=[tool["name"] for tool in tool_calls],
            reasoning_steps=self._build_memory_reasoning_steps(
                sources=sources,
                category=category,
                memory_bundle=memory_bundle
            ),
            memory_metadata=self._build_memory_metadata(
                sources=sources,
                category=category,
                memory_bundle=memory_bundle
            )
        )

        if not saved:
            logger.warning(f"Agent交互写入数据库失败，session_id: {session_id}")

    def _build_messages(
        self,
        question: str,
        docs: List[Document],
        category: str = None,
        memory_bundle: Dict[str, Any] = None
    ) -> List[Dict[str, str]]:
        """构建Agent输入消息"""
        messages: List[Dict[str, str]] = []

        fact_memory = (memory_bundle or {}).get("fact_memory", [])
        if fact_memory:
            if hasattr(self.memory, "format_fact_memory"):
                fact_text = self.memory.format_fact_memory(fact_memory)
            else:
                fact_text = "\n".join(f"- {item.get('fact_value', '')}" for item in fact_memory)

            messages.append({
                "role": "system",
                "content": (
                    "以下是用户已确认的稳定背景信息，请优先将其视为高优先级上下文，"
                    "回答时保持一致，不要忽略：\n"
                    f"{fact_text}"
                )
            })

        summary_memory = (memory_bundle or {}).get("summary_memory", "")
        if summary_memory:
            messages.append({
                "role": "system",
                "content": (
                    "以下是当前会话此前阶段的摘要，请保持上下文连续，避免重复询问：\n"
                    f"{summary_memory}"
                )
            })

        memory_messages = (memory_bundle or {}).get("short_term_messages", [])
        if memory_messages:
            messages.append({
                "role": "system",
                "content": "以下是当前用户最近几轮对话，请结合这些历史保持回答连续一致，不要忽略用户此前已经说明的信息。"
            })
            messages.extend(memory_messages)

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

        # 单轮运行使用独立thread_id，跨轮记忆由数据库负责
        runtime_thread_id = self._build_runtime_thread_id(thread_id)
        config = {"configurable": {"thread_id": runtime_thread_id}}
        filter_dict = self.rag_chain.build_filter_dict(category)

        try:
            memory_bundle = self._get_memory_bundle(thread_id, question)
            retrieval = self.rag_chain.retriever.retrieve_with_diagnostics(
                query=question,
                k=k,
                filter_dict=filter_dict
            )
            docs = retrieval["documents"]
            low_confidence = retrieval["low_confidence"]
            best_score = retrieval["best_score"]

            # 调用Agent
            result = self.agent.invoke(
                {"messages": self._build_messages(question, docs, category, memory_bundle)},
                config=config
            )

            # 回溯提取最后一条真正的文本回答，避免把工具调用块当正文
            answer = self._extract_final_answer(result["messages"])
            if low_confidence and answer:
                answer = f"{self.rag_chain.build_low_confidence_notice(best_score)}\n\n{answer}"

            # 提取工具调用信息
            tool_calls = []
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_calls.extend(msg.tool_calls)

            normalized_tool_calls = self._normalize_tool_calls(tool_calls)
            sources = self.rag_chain.serialize_sources(docs)

            self._save_memory_interaction(
                session_id=thread_id,
                question=question,
                answer=answer,
                tool_calls=normalized_tool_calls,
                sources=sources,
                category=category,
                memory_bundle=memory_bundle
            )

            memory_debug = memory_bundle.get("debug_info", {})
            memory_applied = any([
                memory_debug.get("memory_message_count", 0) > 0,
                memory_debug.get("fact_count", 0) > 0,
                memory_debug.get("summary_applied", False),
            ])

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
                    "used_chat_mode": len(sources) == 0,
                    "low_confidence": low_confidence,
                    "best_score": best_score,
                    "fallback_reason": "no_retrieval" if len(sources) == 0 else ("low_confidence" if low_confidence else None),
                    "retrieval_strategy": retrieval.get("retrieval_strategy"),
                    "vector_result_count": retrieval.get("vector_result_count", 0),
                    "keyword_result_count": retrieval.get("keyword_result_count", 0),
                    "merged_result_count": retrieval.get("merged_result_count", 0),
                    "rewritten_query": retrieval.get("rewritten_query"),
                    "memory_applied": memory_applied,
                    "memory_message_count": memory_debug.get("memory_message_count", 0),
                    "fact_memory_count": memory_debug.get("fact_count", 0),
                    "summary_memory_applied": memory_debug.get("summary_applied", False),
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
                    "used_chat_mode": True,
                    "low_confidence": False,
                    "best_score": None,
                    "fallback_reason": "error",
                    "retrieval_strategy": "hybrid",
                    "vector_result_count": 0,
                    "keyword_result_count": 0,
                    "merged_result_count": 0,
                    "rewritten_query": None,
                    "memory_applied": False,
                    "memory_message_count": 0,
                    "fact_memory_count": 0,
                    "summary_memory_applied": False,
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
            runtime_thread_id = self._build_runtime_thread_id(thread_id)
            config = {"configurable": {"thread_id": runtime_thread_id}}
            filter_dict = self.rag_chain.build_filter_dict(category)
            memory_bundle = self._get_memory_bundle(thread_id, question)
            retrieval = self.rag_chain.retriever.retrieve_with_diagnostics(
                query=question,
                k=k,
                filter_dict=filter_dict
            )
            docs = retrieval["documents"]
            low_confidence = retrieval["low_confidence"]
            best_score = retrieval["best_score"]
            sources = self.rag_chain.serialize_sources(docs)
            messages = self._build_messages(question, docs, category, memory_bundle)
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

            if low_confidence:
                notice = self.rag_chain.build_low_confidence_notice(best_score)
                answer_parts.append(f"{notice}\n\n")
                yield {
                    "type": "content",
                    "content": f"{notice}\n\n"
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

            self._save_memory_interaction(
                session_id=thread_id,
                question=question,
                answer=answer,
                tool_calls=tool_calls,
                sources=sources,
                category=category,
                memory_bundle=memory_bundle
            )

            memory_debug = memory_bundle.get("debug_info", {})
            memory_applied = any([
                memory_debug.get("memory_message_count", 0) > 0,
                memory_debug.get("fact_count", 0) > 0,
                memory_debug.get("summary_applied", False),
            ])

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
                    "used_chat_mode": len(sources) == 0,
                    "low_confidence": low_confidence,
                    "best_score": best_score,
                    "fallback_reason": "no_retrieval" if len(sources) == 0 else ("low_confidence" if low_confidence else None),
                    "retrieval_strategy": retrieval.get("retrieval_strategy"),
                    "vector_result_count": retrieval.get("vector_result_count", 0),
                    "keyword_result_count": retrieval.get("keyword_result_count", 0),
                    "merged_result_count": retrieval.get("merged_result_count", 0),
                    "rewritten_query": retrieval.get("rewritten_query"),
                    "memory_applied": memory_applied,
                    "memory_message_count": memory_debug.get("memory_message_count", 0),
                    "fact_memory_count": memory_debug.get("fact_count", 0),
                    "summary_memory_applied": memory_debug.get("summary_applied", False),
                }
            }
        except Exception as e:
            logger.error(f"流式查询失败: {e}")
            yield {"type": "error", "error": str(e)}


# 全局Agent实例
medical_agent = MedicalAgent()
