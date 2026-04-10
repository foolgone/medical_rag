"""通知组件 - 可复用的通知小组件"""
import streamlit as st
from datetime import datetime


def toast_success(message: str, duration: int = 3):
    """
    成功通知

    Args:
        message: 通知消息
        duration: 显示时长（秒，仅提示作用，Streamlit不支持自动消失）
    """
    st.success(f"✅ {message}")


def toast_error(message: str):
    """
    错误通知

    Args:
        message: 通知消息
    """
    st.error(f"❌ {message}")


def toast_warning(message: str):
    """
    警告通知

    Args:
        message: 通知消息
    """
    st.warning(f"⚠️ {message}")


def toast_info(message: str):
    """
    信息通知

    Args:
        message: 通知消息
    """
    st.info(f"ℹ️ {message}")


def operation_log_entry(operation: str, result: str, success: bool = True,
                        timestamp: str = ""):
    """
    操作日志条目

    Args:
        operation: 操作名称
        result: 操作结果
        success: 是否成功
        timestamp: 时间戳
    """
    if not timestamp:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_color = '#52c41a' if success else '#ff4d4f'

    st.markdown(f"""
    <div style="padding: 0.5rem; margin: 0.3rem 0; background: #fafafa; 
               border-radius: 0.3rem; border-left: 3px solid {log_color};">
        <p style="margin: 0; font-size: 0.8rem; color: #666;">
            <strong>{timestamp}</strong> - {operation}<br>
            <span style="color: {log_color};">{result}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)


def progress_indicator(step: int, total_steps: int, step_name: str = ""):
    """
    进度指示器

    Args:
        step: 当前步骤
        total_steps: 总步骤数
        step_name: 步骤名称
    """
    progress = step / total_steps
    st.progress(progress)

    if step_name:
        st.caption(f"步骤 {step}/{total_steps}: {step_name}")
