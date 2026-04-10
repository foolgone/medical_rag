"""知识库日志组件"""
import streamlit as st
from app.state_manager import state_manager


def render_kb_logs():
    """渲染操作日志区域"""
    st.subheader("📝 操作日志")

    logs = state_manager.operation_logs

    if logs:
        for log in reversed(logs[-10:]):
            _render_log_entry(log)
    else:
        st.caption("暂无操作日志")

    if logs:
        if st.button("🗑️ 清空日志", key="clear_logs"):
            state_manager.clear_operation_logs()
            st.rerun()


def _render_log_entry(log: dict):
    """渲染日志条目"""
    timestamp = log.get('timestamp', '')
    operation = log.get('operation', '')
    result = log.get('result', '')
    log_color = '#52c41a' if log.get('success', False) else '#ff4d4f'

    st.markdown(f"""
    <div style="padding: 0.5rem; margin: 0.3rem 0; background: #fafafa; 
               border-radius: 0.3rem; border-left: 3px solid {log_color};">
        <p style="margin: 0; font-size: 0.8rem; color: #666;">
            <strong>{timestamp}</strong> - {operation}<br>
            <span style="color: {log_color};">{result}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
