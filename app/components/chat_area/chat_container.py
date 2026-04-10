"""聊天容器主组件"""
import streamlit as st
from app.api_client import APIClient
from app.components.chat_area.chat_header import render_chat_header
from app.components.chat_area.message_display import render_chat_messages
from app.components.chat_area.chat_input import render_chat_input
from app.components.chat_area.chat_helpers import has_knowledge_base_files, show_knowledge_base_hint


def render_chat_area(api_client: APIClient, settings: dict):
    """渲染聊天区域"""
    if not has_knowledge_base_files(api_client):
        show_knowledge_base_hint()

    render_chat_header()
    render_chat_messages(settings.get('show_tool_calls', True))
    render_chat_input(api_client, settings)
