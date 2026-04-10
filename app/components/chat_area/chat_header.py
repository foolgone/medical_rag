"""聊天头部组件 - 顶部操作栏"""
import streamlit as st


def render_chat_header():
    """渲染聊天头部：对话标题 + 快捷操作"""
    col_title, col_actions = st.columns([3, 1])

    with col_title:
        _render_chat_title()

    with col_actions:
        _render_action_buttons()


def _render_chat_title():
    """渲染对话标题"""
    if 'chat_title' not in st.session_state:
        st.session_state.chat_title = "Agent智能对话"

    chat_title = st.text_input(
        "对话标题",
        value=st.session_state.chat_title,
        label_visibility="collapsed",
        key="chat_title_input"
    )
    st.session_state.chat_title = chat_title


def _render_action_buttons():
    """渲染操作按钮"""
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        _render_clear_button()

    with col_btn2:
        _render_export_button()

    with col_btn3:
        _render_knowledge_base_button()


def _render_clear_button():
    """渲染清空按钮"""
    if st.button("🗑️ 清空", help="清空当前对话", use_container_width=True):
        if st.warning("确定清空当前对话吗？"):
            if st.button("✅ 确认", key="confirm_clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()


def _render_export_button():
    """渲染导出按钮"""
    if st.button("📥 导出", help="导出对话记录", use_container_width=True):
        export_conversation()


def _render_knowledge_base_button():
    """渲染知识库按钮"""
    if st.button("📚 知识库", help="切换知识库", use_container_width=True):
        st.info("知识库切换功能开发中...")


def export_conversation():
    """导出对话记录"""
    if not st.session_state.messages:
        st.warning("暂无对话记录可导出")
        return

    try:
        from datetime import datetime

        export_text = f"# 对话记录\n\n"
        export_text += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        export_text += "---\n\n"

        for msg in st.session_state.messages:
            role = "用户" if msg["role"] == "user" else "AI助手"
            export_text += f"**{role}:**\n\n{msg['content']}\n\n---\n\n"

        st.download_button(
            label="📥 下载对话记录",
            data=export_text,
            file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )

    except Exception as e:
        st.error(f"导出失败: {e}")
