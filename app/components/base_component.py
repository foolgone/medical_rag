"""组件基类 - 定义组件通用接口"""
from abc import ABC, abstractmethod
from typing import Any, Dict
import streamlit as st


class BaseComponent(ABC):
    """基础组件类"""
    
    def __init__(self, key: str = ""):
        self.key = key
    
    @abstractmethod
    def render(self, **kwargs) -> Any:
        """渲染组件"""
        pass
    
    def render_container(self, **kwargs):
        """在容器中渲染"""
        with st.container():
            return self.render(**kwargs)
    
    def render_expander(self, label: str = "", **kwargs):
        """在展开器中渲染"""
        with st.expander(label):
            return self.render(**kwargs)


class InteractiveComponent(BaseComponent):
    """交互式组件基类"""
    
    def __init__(self, key: str = "", on_click=None):
        super().__init__(key)
        self.on_click = on_click
    
    def handle_interaction(self, *args, **kwargs):
        """处理交互事件"""
        if self.on_click:
            self.on_click(*args, **kwargs)
