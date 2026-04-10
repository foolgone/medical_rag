"""聊天处理器 - 消息处理逻辑"""
import streamlit as st
from app.api_client import APIClient
from app.state_manager import state_manager


def handle_stream_query(api_client: APIClient, question: str, settings: dict):
    """流式查询处理"""
    status_placeholder = st.empty()
    content_placeholder = st.empty()

    content = ""
    tool_calls = []
    references = []

    try:
        _show_loading_status(status_placeholder, "🔍 正在检索知识库...", "#1976d2")

        for event in api_client.query_stream(
                question,
                settings.get('session_id', 'default'),
                settings.get('top_k', 5)
        ):
            event_type = event.get("type")

            if event_type == "tool_call":
                tool_calls.extend(event.get("tools", []))
                _show_loading_status(status_placeholder, "🔧 正在调用工具...", "#4caf50")

            elif event_type == "retrieval":
                docs = event.get("documents", [])
                if docs:
                    references = [{"filename": doc.get("metadata", {}).get("source", "未知")}
                                  for doc in docs[:3]]

            elif event_type == "content":
                _show_loading_status(status_placeholder, "✍️ 正在生成回复...", "#ff9800")
                content += event.get("content", "")
                _show_streaming_content(content_placeholder, content)

            elif event_type == "end":
                status_placeholder.empty()
                content_placeholder.empty()

                state_manager.add_message(
                    "assistant",
                    content,
                    tool_calls=tool_calls,
                    references=references
                )
                st.rerun()
                return

    except Exception as e:
        status_placeholder.empty()
        content_placeholder.empty()
        st.error(f"❌ 查询失败: {e}")


def handle_normal_query(api_client: APIClient, question: str, settings: dict):
    """普通查询处理"""
    with st.spinner("🤖 Agent正在处理..."):
        try:
            result = api_client.query(
                question,
                settings.get('session_id', 'default'),
                settings.get('top_k', 5)
            )

            ai_message = {
                "role": "assistant",
                "content": result.get("answer", ""),
                "tool_calls_count": result.get("tool_calls_count", 0)
            }

            if result.get("sources"):
                ai_message["references"] = [
                    {"filename": src.get("source", "未知")}
                    for src in result["sources"][:3]
                ]

            state_manager.messages.append(ai_message)
            st.rerun()

        except Exception as e:
            st.error(f"❌ 查询失败: {e}")


def _show_loading_status(placeholder, message: str, color: str):
    """显示加载状态"""
    placeholder.markdown(f'''
    <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; 
               background: #e3f2fd; border-radius: 0.5rem;">
        <div style="width: 16px; height: 16px; border: 2px solid {color}; 
                   border-top-color: transparent; border-radius: 50%; 
                   animation: spin 1s linear infinite;"></div>
        <span style="font-size: 0.9rem; color: {color};">{message}</span>
    </div>
    <style>
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
    ''', unsafe_allow_html=True)


def _show_streaming_content(placeholder, content: str):
    """显示流式内容"""
    placeholder.markdown(f'''
    <div style="display: flex; justify-content: flex-start; margin: 0.5rem 0;">
        <div style="max-width: 70%; padding: 1rem; background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%); 
                   border-radius: 1rem 1rem 1rem 0.2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="font-size: 0.85rem; color: #666; margin-bottom: 0.3rem;">
                <strong>🤖 AI助手</strong>
            </div>
            <div style="font-size: 0.95rem; line-height: 1.6; color: #333;">
                {content}▌
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
