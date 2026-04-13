
"""聊天页面 - 整合聊天功能"""
import streamlit as st
from app.pages.base_page import BasePage
from app.components.chat_area import render_chat_area
from app.state_manager import state_manager


class ChatPage(BasePage):
    """聊天页面"""

    def render(self):
        """渲染聊天页面"""
        # 获取设置
        settings = {
            'api_url': state_manager.api_url,
            'session_id': state_manager.session_id,
            'top_k': state_manager.top_k,
            'query_category': state_manager.query_category,
            'query_mode': state_manager.query_mode,
            'enable_streaming': state_manager.enable_streaming,
            'show_tool_calls': state_manager.show_tool_calls
        }

        # 渲染聊天区域
        render_chat_area(self.api_client, settings)
