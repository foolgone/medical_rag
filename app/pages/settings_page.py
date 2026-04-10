
"""设置页面 - 整合系统设置功能"""
import streamlit as st
from app.pages.base_page import BasePage
from app.components.settings import render_settings_module


class SettingsPage(BasePage):
    """设置页面"""

    def render(self):
        """渲染设置页面"""
        render_settings_module(self.api_client, self.config)
