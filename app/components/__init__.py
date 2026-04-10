"""组件包初始化"""
from app.components.chat_area import render_chat_area
from app.components.knowledge_base import render_knowledge_base_module
from app.components.settings import render_settings_module

__all__ = [
    'render_chat_area',
    'render_knowledge_base_module',
    'render_settings_module'
]
