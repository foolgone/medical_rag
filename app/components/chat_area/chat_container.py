"""聊天容器主组件"""
import streamlit as st
from app.api_client import APIClient
from app.components.chat_area.chat_header import render_chat_header
from app.components.chat_area.message_display import render_chat_messages
from app.components.chat_area.chat_input import render_chat_input
from app.components.chat_area.chat_handlers import handle_stream_query, handle_normal_query
from app.components.chat_area.chat_helpers import has_knowledge_base_files, show_knowledge_base_hint


def render_chat_area(api_client: APIClient, settings: dict):
    """渲染聊天区域"""
    if not has_knowledge_base_files(api_client):
        show_knowledge_base_hint()

    render_chat_header()
    render_chat_messages(settings.get('show_tool_calls', True))

    # 若上一轮提交了问题，这一轮在“消息已渲染后”再发起请求，避免提交后界面空白。
    pending_question = st.session_state.pop("pending_chat_question", None)
    if pending_question:
        if settings.get("enable_streaming", True):
            handle_stream_query(api_client, pending_question, settings)
        else:
            handle_normal_query(api_client, pending_question, settings)

    render_chat_input(api_client, settings)
