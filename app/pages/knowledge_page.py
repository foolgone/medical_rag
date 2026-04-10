
"""知识库页面 - 整合知识库管理功能"""
import streamlit as st
from app.pages.base_page import BasePage
from app.components.knowledge_base import render_knowledge_base_module


class KnowledgePage(BasePage):
    """知识库页面"""

    def render(self):
        """渲染知识库页面"""
        render_knowledge_base_module(self.api_client)
