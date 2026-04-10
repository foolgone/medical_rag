"""按钮组件 - 可复用的按钮小组件"""
import streamlit as st
from typing import Optional, Callable


def primary_button(label: str, key: str = "", on_click: Optional[Callable] = None,
                   use_container_width: bool = False, help_text: str = "") -> bool:
    """
    主要按钮

    Args:
        label: 按钮文本
        key: 唯一键
        on_click: 点击回调
        use_container_width: 是否占满容器宽度
        help_text: 帮助文本

    Returns:
        是否被点击
    """
    clicked = st.button(
        label,
        key=key,
        type="primary",
        use_container_width=use_container_width,
        help=help_text
    )

    if clicked and on_click:
        on_click()

    return clicked


def secondary_button(label: str, key: str = "", on_click: Optional[Callable] = None,
                     use_container_width: bool = False, help_text: str = "") -> bool:
    """
    次要按钮

    Args:
        label: 按钮文本
        key: 唯一键
        on_click: 点击回调
        use_container_width: 是否占满容器宽度
        help_text: 帮助文本

    Returns:
        是否被点击
    """
    clicked = st.button(
        label,
        key=key,
        type="secondary",
        use_container_width=use_container_width,
        help=help_text
    )

    if clicked and on_click:
        on_click()

    return clicked


def danger_button(label: str, key: str = "", on_click: Optional[Callable] = None,
                  use_container_width: bool = False, help_text: str = "") -> bool:
    """
    危险操作按钮（红色）

    Args:
        label: 按钮文本
        key: 唯一键
        on_click: 点击回调
        use_container_width: 是否占满容器宽度
        help_text: 帮助文本

    Returns:
        是否被点击
    """
    # Streamlit没有danger类型，使用自定义样式
    clicked = st.button(
        label,
        key=key,
        use_container_width=use_container_width,
        help=help_text
    )

    if clicked and on_click:
        on_click()

    return clicked
