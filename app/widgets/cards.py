"""卡片组件 - 可复用的卡片小组件"""
import streamlit as st


def info_card(title: str, content: str, icon: str = "ℹ️",
              border_color: str = "#1677ff", bg_color: str = "#f0f9ff"):
    """
    信息卡片

    Args:
        title: 卡片标题
        content: 卡片内容
        icon: 图标
        border_color: 边框颜色
        bg_color: 背景颜色
    """
    st.markdown(f"""
    <div style="padding: 1rem; background: {bg_color}; border-radius: 0.5rem; 
               border-left: 4px solid {border_color}; margin-bottom: 1rem;">
        <h4 style="margin: 0 0 0.5rem 0; color: {border_color};">
            {icon} {title}
        </h4>
        <p style="margin: 0; font-size: 0.9rem; color: #666;">
            {content}
        </p>
    </div>
    """, unsafe_allow_html=True)


def stat_card(label: str, value: str, icon: str = "📊",
              subtext: str = "", bg_color: str = "white"):
    """
    统计卡片

    Args:
        label: 标签
        value: 数值
        icon: 图标
        subtext: 副文本
        bg_color: 背景颜色
    """
    subtext_html = f"<br><span style='font-size: 0.75rem; color: #999;'>{subtext}</span>" if subtext else ""

    st.markdown(f"""
    <div style="padding: 1rem; background: {bg_color}; border-radius: 0.5rem; 
               box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{icon}</div>
        <div style="font-size: 1.8rem; font-weight: bold; color: #1677ff; margin: 0.3rem 0;">
            {value}
        </div>
        <div style="font-size: 0.85rem; color: #666; margin: 0;">
            {label}{subtext_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def status_badge(status: str, color: str = "#52c41a"):
    """
    状态徽章

    Args:
        status: 状态文本
        color: 颜色
    """
    st.markdown(f"""
    <span style="display: inline-block; padding: 0.2rem 0.6rem; 
                background: {color}20; color: {color}; 
                border-radius: 1rem; font-size: 0.75rem; font-weight: 500;">
        {status}
    </span>
    """, unsafe_allow_html=True)
