
"""页面基类 - 定义页面通用接口"""
from abc import ABC, abstractmethod
import streamlit as st
from app.api_client import APIClient
from app.config import AppConfig


class BasePage(ABC):
    """基础页面类"""
    
    def __init__(self, api_client: APIClient, config: AppConfig):
        self.api_client = api_client
        self.config = config
    
    @abstractmethod
    def render(self):
        """渲染页面"""
        pass
    
    def render_header(self, title: str):
        """渲染页面标题"""
        st.markdown(f"""
        <h2 style="color: #1677ff; margin-bottom: 1.5rem;">{title}</h2>
        """, unsafe_allow_html=True)
    
    def render_info_box(self, message: str, info_type: str = "info"):
        """渲染信息框"""
        colors = {
            "info": "#f0f9ff",
            "warning": "#fff9e6",
            "success": "#f6ffed",
            "error": "#fff2f0"
        }
        borders = {
            "info": "#1677ff",
            "warning": "#faad14",
            "success": "#52c41a",
            "error": "#ff4d4f"
        }
        
        color = colors.get(info_type, colors["info"])
        border = borders.get(info_type, borders["info"])
        
        st.markdown(f"""
        <div style="padding: 1rem; background: {color}; border-radius: 0.5rem; 
                   border-left: 4px solid {border}; margin-bottom: 1.5rem;">
            <p style="margin: 0; font-size: 0.9rem; color: #666;">
                {message}
            </p>
        </div>
        """, unsafe_allow_html=True)
