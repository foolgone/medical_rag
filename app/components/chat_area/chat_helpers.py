"""聊天辅助函数"""
import streamlit as st
from app.api_client import APIClient


def has_knowledge_base_files(api_client: APIClient) -> bool:
    """检查是否有知识库文件"""
    try:
        stats = api_client.get_stats()
        return stats.get('total_files', 0) > 0
    except Exception:
        return False


def show_knowledge_base_hint():
    """显示知识库提示"""
    st.markdown("""
    <div style="padding: 1.5rem; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
               border-radius: 0.5rem; border-left: 4px solid #1976d2; margin: 1rem 0;">
        <h3 style="margin: 0 0 0.5rem 0; color: #1976d2;">💡 开始使用</h3>
        <p style="margin: 0; font-size: 0.9rem; color: #555;">
            请先切换到<strong>"📄 文档知识库"</strong>模块，上传医学文档并更新知识库，<br>
            然后回到这里开始智能问答。
        </p>
    </div>
    """, unsafe_allow_html=True)
