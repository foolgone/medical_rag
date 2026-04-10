"""
RAG检索工具 - 将现有RAG系统封装为Agent可调用的工具
"""
from langchain.tools import tool
from rag.rag_chain import MedicalRAGChain

# 单例模式避免重复初始化
_rag_chain = None


def get_rag_chain() -> MedicalRAGChain:
    """获取RAG链单例"""
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = MedicalRAGChain()
    return _rag_chain


@tool
def search_medical_knowledge(query: str, k: int = 3) -> str:
    """
    从医疗知识库中检索相关信息

    Args:
        query: 检索查询
        k: 返回文档数量

    Returns:
        格式化的相关知识内容
    """
    try:
        rag_chain = get_rag_chain()
        docs = rag_chain.retriever.retrieve(query, k=k)

        if not docs:
            return "未在知识库中找到相关信息"

        # 格式化检索结果
        context = rag_chain.retriever.format_context(docs)
        return context
    except Exception as e:
        return f"检索失败：{str(e)}"


@tool
def get_disease_info(disease_name: str) -> str:
    """
    查询特定疾病的详细信息

    Args:
        disease_name: 疾病名称

    Returns:
        疾病相关信息（症状、治疗、预防等）
    """
    query = f"{disease_name} 症状 治疗 预防"
    return search_medical_knowledge.invoke(query)
