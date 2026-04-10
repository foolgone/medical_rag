"""消息显示组件 - 渲染聊天消息"""
import streamlit as st
from app.state_manager import state_manager


# 最大渲染消息数，避免大量消息导致卡顿
MAX_DISPLAY_MESSAGES = 50


def render_chat_messages(show_tools: bool = True):
    """渲染所有聊天消息（限制数量以提升性能）"""
    chat_container = st.container()

    # 使用 state_manager 安全地获取消息列表
    messages = state_manager.messages

    # 只渲染最近的消息
    messages_to_display = messages[-MAX_DISPLAY_MESSAGES:] if len(messages) > MAX_DISPLAY_MESSAGES else messages

    # 如果消息超过限制，显示提示
    if len(messages) > MAX_DISPLAY_MESSAGES:
        hidden_count = len(messages) - MAX_DISPLAY_MESSAGES
        st.info(f"📝 仅显示最近 {MAX_DISPLAY_MESSAGES} 条消息（共 {len(messages)} 条）")

    with chat_container:
        for idx, message in enumerate(messages_to_display):
            display_message(message, show_tools, idx)

    if messages:
        st.markdown("<div id='chat-bottom'></div>", unsafe_allow_html=True)


def display_message(message: dict, show_tools: bool = True, index: int = 0):
    """显示单条消息"""
    if message["role"] == "user":
        _display_user_message(message)
    else:
        _display_assistant_message(message, show_tools)


def _display_user_message(message: dict):
    """显示用户消息"""
    st.markdown(
        f'<div style="display: flex; justify-content: flex-end; margin: 0.5rem 0;">'
        f'<div style="max-width: 70%; padding: 1rem; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); '
        f'border-radius: 1rem 1rem 0.2rem 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
        f'<div style="font-size: 0.85rem; color: #1976d2; margin-bottom: 0.3rem;">'
        f'<strong>👤 您</strong></div>'
        f'<div style="font-size: 0.95rem; line-height: 1.6; color: #333;">'
        f'{message["content"]}</div></div></div>',
        unsafe_allow_html=True
    )


def _display_assistant_message(message: dict, show_tools: bool):
    """显示AI助手消息"""
    tool_html = _build_tool_calls_html(message, show_tools)
    reference_html = _build_references_html(message)

    st.markdown(
        f'<div style="display: flex; justify-content: flex-start; margin: 0.5rem 0;">'
        f'<div style="max-width: 70%; padding: 1rem; background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%); '
        f'border-radius: 1rem 1rem 1rem 0.2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
        f'<div style="font-size: 0.85rem; color: #666; margin-bottom: 0.3rem;">'
        f'<strong>🤖 AI助手</strong></div>'
        f'<div style="font-size: 0.95rem; line-height: 1.6; color: #333;">'
        f'{message["content"]}</div>'
        f'{tool_html}{reference_html}'
        f'</div></div>',
        unsafe_allow_html=True
    )


def _build_tool_calls_html(message: dict, show_tools: bool) -> str:
    """构建工具调用HTML"""
    if not message.get("tool_calls") or not show_tools:
        return ""

    tools = ", ".join([t.get("name", "?") for t in message["tool_calls"]])

    return (
        f'<div style="margin-top: 0.5rem; padding: 0.5rem; background: #e8f5e9; '
        f'border-radius: 0.5rem; border-left: 3px solid #4caf50;">'
        f'<p style="margin: 0; font-size: 0.8rem; color: #2e7d32;">'
        f'<strong>🔧 工具调用:</strong> {tools}</p></div>'
    )


def _build_references_html(message: dict) -> str:
    """构建引用HTML"""
    if not message.get("references"):
        return ""

    refs = message["references"]
    ref_items = []
    for ref in refs[:3]:
        ref_items.append(f"• {ref.get('filename', '未知文件')}")

    return (
        f'<div style="margin-top: 0.5rem; padding: 0.5rem; background: #fff3e0; '
        f'border-radius: 0.5rem; border-left: 3px solid #ff9800;">'
        f'<p style="margin: 0; font-size: 0.8rem; color: #e65100;">'
        f'<strong>📚 参考知识库文件:</strong></p>'
        f'<p style="margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #666;">'
        f'{"<br>".join(ref_items)}</p></div>'
    )

