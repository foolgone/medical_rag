"""聊天输入组件 - 底部输入区域"""
import streamlit as st
from app.api_client import APIClient
from app.state_manager import state_manager
from app.components.chat_area.chat_handlers import handle_stream_query, handle_normal_query


def render_chat_input(api_client: APIClient, settings: dict):
    """渲染聊天输入区域"""
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    question = st.chat_input(
        placeholder="请输入您的医疗问题（可基于已上传的知识库提问）...",
        key="chat_input"
    )

    if question:
        # 先把用户消息写入并触发一次 rerun，让 UI 先渲染历史与占位；
        # 下一轮再处理耗时请求，避免出现“提交后界面发白/空白感”。
        state_manager.add_message("user", question)
        st.session_state.pending_chat_question = question
        st.rerun()

    _render_disclaimer()


def _render_disclaimer():
    """渲染免责声明"""
    st.markdown("""
    <div style="text-align: center; padding: 0.5rem; margin-top: 0.5rem; 
               background: #fff9e6; border-radius: 0.3rem; border: 1px solid #ffe58f;">
        <p style="margin: 0; font-size: 0.75rem; color: #ad6800;">
            ⚠️ 本回复基于上传的知识库生成，仅供参考，不能替代专业医疗建议
        </p>
    </div>
    """, unsafe_allow_html=True)


def handle_user_message(api_client: APIClient, question: str, settings: dict):
    """处理用户消息"""
    state_manager.add_message("user", question)

    if settings.get('enable_streaming', True):
        handle_stream_query(api_client, question, settings)
    else:
        handle_normal_query(api_client, question, settings)

