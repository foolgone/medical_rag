
"""
Ollama LLM客户端模块
提供与大语言模型的交互接口
"""
from typing import Optional, List, AsyncGenerator
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import settings
from loguru import logger
import json


class MedicalLLMClient:
    """医疗LLM客户端"""
    
    def __init__(
        self,
        model_name: str = None,
        base_url: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """
        初始化LLM客户端
        
        Args:
            model_name: 模型名称
            base_url: Ollama服务地址
            temperature: 温度参数（创造性）
            max_tokens: 最大生成token数
        """
        self.model_name = model_name or settings.LLM_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.llm = ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
            num_predict=self.max_tokens
        )
        logger.info(f"LLM客户端初始化完成 - 模型: {self.model_name}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成回答
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            
        Returns:
            生成的文本
        """
        try:
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加用户问题
            messages.append(HumanMessage(content=prompt))
            
            # 生成回答
            response = self.llm.invoke(messages)
            answer = response.content
            
            logger.debug(f"LLM生成完成，回答长度: {len(answer)}")
            return answer
        except Exception as e:
            logger.error(f"LLM生成失败: {e}")
            raise
    
    def generate_with_context(
        self,
        question: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        基于上下文生成回答（RAG模式）
        
        Args:
            question: 用户问题
            context: 检索的上下文
            system_prompt: 系统提示
            
        Returns:
            生成的回答
        """
        default_system_prompt = """你是一个专业的医疗助手，基于提供的医学知识回答问题。
请遵循以下原则：
1. 只基于提供的上下文信息回答问题
2. 如果上下文中没有足够信息，请说明"根据现有资料无法确定"
3. 回答要专业、准确、易懂
4. 必要时提醒用户咨询专业医生"""

        system_prompt = system_prompt or default_system_prompt
        
        # 构建带上下文的提示
        full_prompt = f"""基于以下医学知识：

{context}

请回答这个问题：{question}

回答："""
        
        try:
            answer = self.generate(full_prompt, system_prompt)
            logger.info("基于上下文的回答生成完成")
            return answer
        except Exception as e:
            logger.error(f"基于上下文的回答生成失败: {e}")
            raise
    
    async def generate_stream(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成回答
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            
        Yields:
            生成的文本片段
        """
        try:
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加用户问题
            messages.append(HumanMessage(content=prompt))
            
            # 流式生成回答
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    yield chunk.content
            
            logger.debug("流式LLM生成完成")
        except Exception as e:
            logger.error(f"流式LLM生成失败: {e}")
            raise

    def chat(self, messages: List[dict]) -> str:
        """
        多轮对话
        
        Args:
            messages: 消息列表，格式为 [{"role": "user/assistant/system", "content": "..."}]
            
        Returns:
            AI回复
        """
        try:
            langchain_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    langchain_messages.append(AIMessage(content=content))
            
            response = self.llm.invoke(langchain_messages)
            answer = response.content
            
            logger.debug(f"对话生成完成，回答长度: {len(answer)}")
            return answer
        except Exception as e:
            logger.error(f"对话生成失败: {e}")
            raise
