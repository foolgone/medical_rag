"""
应用状态管理器 - 统一管理Streamlit会话状态
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import streamlit as st


class StateManager:
    """状态管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """初始化所有会话状态"""
        # 导航状态
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "chat"

        # 聊天状态
        if 'messages' not in st.session_state:
            st.session_state.messages = []

        if 'chat_title' not in st.session_state:
            st.session_state.chat_title = "Agent智能对话"

        # 会话ID
        if 'session_id' not in st.session_state:
            st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 设置状态
        if 'api_url' not in st.session_state:
            st.session_state.api_url = "http://localhost:8000/api/v1"

        if 'top_k' not in st.session_state:
            st.session_state.top_k = 5

        if 'query_category' not in st.session_state:
            st.session_state.query_category = "all"

        if 'query_mode' not in st.session_state:
            st.session_state.query_mode = "agent"

        if 'enable_streaming' not in st.session_state:
            st.session_state.enable_streaming = True

        if 'show_tool_calls' not in st.session_state:
            st.session_state.show_tool_calls = True

        # 知识库状态
        if 'kb_refresh' not in st.session_state:
            st.session_state.kb_refresh = 0

        if 'operation_logs' not in st.session_state:
            st.session_state.operation_logs = []

    @property
    def current_page(self) -> str:
        return st.session_state.get('current_page', 'chat')

    @current_page.setter
    def current_page(self, value: str):
        st.session_state.current_page = value

    @property
    def messages(self) -> List[Dict]:
        return st.session_state.get('messages', [])

    @messages.setter
    def messages(self, value: List[Dict]):
        st.session_state.messages = value

    def add_message(self, role: str, content: str, **kwargs):
        """添加消息"""
        if 'messages' not in st.session_state:
            st.session_state.messages = []

        message = {
            "role": role,
            "content": content,
            **kwargs
        }
        st.session_state.messages.append(message)

    @staticmethod
    def clear_messages():
        """清空消息"""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        st.session_state.messages = []

    @property
    def session_id(self) -> str:
        return st.session_state.get('session_id', 'default')

    @session_id.setter
    def session_id(self, value: str):
        st.session_state.session_id = value

    @property
    def top_k(self) -> int:
        return st.session_state.get('top_k', 5)

    @top_k.setter
    def top_k(self, value: int):
        st.session_state.top_k = value

    @property
    def query_category(self) -> str:
        return st.session_state.get('query_category', 'all')

    @query_category.setter
    def query_category(self, value: str):
        st.session_state.query_category = value

    @property
    def query_mode(self) -> str:
        return st.session_state.get('query_mode', 'agent')

    @query_mode.setter
    def query_mode(self, value: str):
        st.session_state.query_mode = value

    @property
    def enable_streaming(self) -> bool:
        return st.session_state.get('enable_streaming', True)

    @property
    def show_tool_calls(self) -> bool:
        return st.session_state.get('show_tool_calls', True)

    @property
    def api_url(self) -> str:
        return st.session_state.get('api_url', 'http://localhost:8000/api/v1')

    @api_url.setter
    def api_url(self, value: str):
        st.session_state.api_url = value

    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取设置值"""
        return st.session_state.get(key, default)

    def set_setting(self, key: str, value: Any):
        """设置值"""
        st.session_state[key] = value

    def add_operation_log(self, operation: str, result: str, success: bool = True):
        """添加操作日志"""
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'operation': operation,
            'result': result,
            'success': success
        }

        if 'operation_logs' not in st.session_state:
            st.session_state.operation_logs = []

        st.session_state.operation_logs.append(log_entry)

        # 限制日志数量
        if len(st.session_state.operation_logs) > 50:
            st.session_state.operation_logs = st.session_state.operation_logs[-50:]

    @property
    def operation_logs(self) -> List[Dict]:
        return st.session_state.get('operation_logs', [])

    def clear_operation_logs(self):
        """清空操作日志"""
        st.session_state.operation_logs = []

    def reset_to_defaults(self):
        """恢复默认设置"""
        keys_to_clear = [
            'setting_api_url', 'setting_session_id', 'setting_top_k', 'setting_query_category', 'setting_query_mode',
            'setting_enable_streaming', 'setting_show_tool_calls',
            'setting_similarity_threshold', 'setting_theme',
            'setting_notifications', 'setting_auto_save'
        ]

        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

        # 重置为默认值
        st.session_state.top_k = 5
        st.session_state.query_category = "all"
        st.session_state.query_mode = "agent"
        st.session_state.enable_streaming = True
        st.session_state.show_tool_calls = True

    def save_settings_from_inputs(self):
        """从输入控件保存设置"""
        if 'setting_api_url' in st.session_state:
            st.session_state.api_url = st.session_state.setting_api_url

        if 'setting_session_id' in st.session_state:
            st.session_state.session_id = st.session_state.setting_session_id

        if 'setting_top_k' in st.session_state:
            st.session_state.top_k = st.session_state.setting_top_k

        if 'setting_query_category' in st.session_state:
            st.session_state.query_category = st.session_state.setting_query_category

        if 'setting_query_mode' in st.session_state:
            st.session_state.query_mode = st.session_state.setting_query_mode

        if 'setting_enable_streaming' in st.session_state:
            st.session_state.enable_streaming = st.session_state.setting_enable_streaming

        if 'setting_show_tool_calls' in st.session_state:
            st.session_state.show_tool_calls = st.session_state.setting_show_tool_calls


# 全局状态管理器实例
state_manager = StateManager()
