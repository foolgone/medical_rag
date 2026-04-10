"""聊天区域组件 - 优化版"""
import streamlit as st
from app.api_client import APIClient


def render_chat_area(api_client: APIClient, settings: dict):
    """渲染聊天区域"""

    # 检查是否有知识库文件
    if not has_knowledge_base_files(api_client):
        show_knowledge_base_hint()

    # 顶部操作栏
    render_chat_header()

    # 中间对话区
    render_chat_messages(settings.get('show_tool_calls', True))

    # 底部输入区
    render_chat_input(api_client, settings)


def render_chat_header():
    """顶部操作栏：对话标题 + 快捷操作"""
    col_title, col_actions = st.columns([3, 1])

    with col_title:
        # 对话标题
        if 'chat_title' not in st.session_state:
            st.session_state.chat_title = "Agent智能对话"

        chat_title = st.text_input(
            "对话标题",
            value=st.session_state.chat_title,
            label_visibility="collapsed",
            key="chat_title_input"
        )
        st.session_state.chat_title = chat_title

    with col_actions:
        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            if st.button("🗑️ 清空", help="清空当前对话", use_container_width=True):
                if st.warning("确定清空当前对话吗？"):
                    if st.button("✅ 确认", key="confirm_clear", use_container_width=True):
                        st.session_state.messages = []
                        st.rerun()

        with col_btn2:
            if st.button("📥 导出", help="导出对话记录", use_container_width=True):
                export_conversation()

        with col_btn3:
            if st.button("📚 知识库", help="切换知识库", use_container_width=True):
                st.info("知识库切换功能开发中...")


def render_chat_messages(show_tools: bool = True):
    """中间对话区：用户消息 + AI消息（带引用）"""

    # 对话容器
    chat_container = st.container()

    with chat_container:
        for idx, message in enumerate(st.session_state.messages):
            display_message(message, show_tools, idx)

    # 自动滚动到底部（通过占位符实现）
    if st.session_state.messages:
        st.markdown("<div id='chat-bottom'></div>", unsafe_allow_html=True)


def display_message(message: dict, show_tools: bool = True, index: int = 0):
    """显示单条消息"""

    if message["role"] == "user":
        # 用户消息：右对齐，浅蓝背景
        st.markdown(f'''
        <div style="display: flex; justify-content: flex-end; margin: 0.5rem 0;">
            <div style="max-width: 70%; padding: 1rem; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                       border-radius: 1rem 1rem 0.2rem 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="font-size: 0.85rem; color: #1976d2; margin-bottom: 0.3rem;">
                    <strong>👤 您</strong>
                </div>
                <div style="font-size: 0.95rem; line-height: 1.6; color: #333;">
                    {message["content"]}
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    else:
        # AI消息：左对齐，浅灰背景
        tool_html = ""
        if message.get("tool_calls") and show_tools:
            tools = ", ".join([t.get("name", "?") for t in message["tool_calls"]])
            tool_html = f'''
            <div style="margin-top: 0.5rem; padding: 0.5rem; background: #e8f5e9; 
                       border-radius: 0.5rem; border-left: 3px solid #4caf50;">
                <p style="margin: 0; font-size: 0.8rem; color: #2e7d32;">
                    <strong>🔧 工具调用:</strong> {tools}
                </p>
            </div>
            '''

        # RAG引用提示
        reference_html = ""
        if message.get("references"):
            refs = message["references"]
            ref_items = []
            for ref in refs[:3]:  # 最多显示3个引用
                ref_items.append(f"• {ref.get('filename', '未知文件')}")

            reference_html = f'''
            <div style="margin-top: 0.5rem; padding: 0.5rem; background: #fff3e0; 
                       border-radius: 0.5rem; border-left: 3px solid #ff9800;">
                <p style="margin: 0; font-size: 0.8rem; color: #e65100;">
                    <strong>📚 参考知识库文件:</strong>
                </p>
                <p style="margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #666;">
                    {chr(10).join(ref_items)}
                </p>
            </div>
            '''

        st.markdown(f'''
        <div style="display: flex; justify-content: flex-start; margin: 0.5rem 0;">
            <div style="max-width: 70%; padding: 1rem; background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%); 
                       border-radius: 1rem 1rem 1rem 0.2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="font-size: 0.85rem; color: #666; margin-bottom: 0.3rem;">
                    <strong>🤖 AI助手</strong>
                </div>
                <div style="font-size: 0.95rem; line-height: 1.6; color: #333;">
                    {message["content"]}
                </div>
                {tool_html}
                {reference_html}
            </div>
        </div>
        ''', unsafe_allow_html=True)


def render_chat_input(api_client: APIClient, settings: dict):
    """底部输入区：输入框 + 发送按钮 + 辅助功能"""

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # 输入框
    question = st.chat_input(
        placeholder="请输入您的医疗问题（可基于已上传的知识库提问）...",
        key="chat_input"
    )

    if question:
        handle_user_message(api_client, question, settings)

    # 免责提示
    st.markdown("""
    <div style="text-align: center; padding: 0.5rem; margin-top: 0.5rem; 
               background: #fff9e6; border-radius: 0.3rem; border: 1px solid #ffe58f;">
        <p style="margin: 0; font-size: 0.75rem; color: #ad6800;">
            ⚠️ 本回复基于上传的知识库生成，仅供参考，不能替代专业医疗建议
        </p>
    </div>
    """, unsafe_allow_html=True)


def handle_user_message(api_client: APIClient, question: str, settings: dict):
    """处理用户消息"""

    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": question})

    # 根据设置选择查询方式
    if settings.get('enable_streaming', True):
        handle_stream_query(api_client, question, settings)
    else:
        handle_normal_query(api_client, question, settings)


def handle_stream_query(api_client: APIClient, question: str, settings: dict):
    """流式查询"""

    # 创建占位符
    status_placeholder = st.empty()
    content_placeholder = st.empty()

    content = ""
    tool_calls = []
    references = []

    try:
        # 显示加载状态
        status_placeholder.markdown('''
        <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; 
                   background: #e3f2fd; border-radius: 0.5rem;">
            <div style="width: 16px; height: 16px; border: 2px solid #1976d2; 
                       border-top-color: transparent; border-radius: 50%; 
                       animation: spin 1s linear infinite;"></div>
            <span style="font-size: 0.9rem; color: #1976d2;">🔍 正在检索知识库...</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
        ''', unsafe_allow_html=True)

        # 流式接收响应
        for event in api_client.query_stream(
            question,
            settings.get('session_id', 'default'),
            settings.get('top_k', 5)
        ):
            event_type = event.get("type")

            if event_type == "tool_call":
                tool_calls.extend(event.get("tools", []))
                status_placeholder.markdown('''
                <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; 
                           background: #e8f5e9; border-radius: 0.5rem;">
                    <div style="width: 16px; height: 16px; border: 2px solid #4caf50; 
                               border-top-color: transparent; border-radius: 50%; 
                               animation: spin 1s linear infinite;"></div>
                    <span style="font-size: 0.9rem; color: #2e7d32;">🔧 正在调用工具...</span>
                </div>
                ''', unsafe_allow_html=True)

            elif event_type == "retrieval":
                # 检索到的文档
                docs = event.get("documents", [])
                if docs:
                    references = [{"filename": doc.get("metadata", {}).get("source", "未知")}
                                 for doc in docs[:3]]

            elif event_type == "content":
                # 更新状态为生成中
                status_placeholder.markdown('''
                <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; 
                           background: #fff3e0; border-radius: 0.5rem;">
                    <div style="width: 16px; height: 16px; border: 2px solid #ff9800; 
                               border-top-color: transparent; border-radius: 50%; 
                               animation: spin 1s linear infinite;"></div>
                    <span style="font-size: 0.9rem; color: #e65100;">✍️ 正在生成回复...</span>
                </div>
                ''', unsafe_allow_html=True)

                # 流式显示内容
                content += event.get("content", "")
                content_placeholder.markdown(f'''
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

            elif event_type == "end":
                # 完成
                status_placeholder.empty()
                content_placeholder.empty()

                # 保存完整消息
                ai_message = {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                    "references": references
                }
                st.session_state.messages.append(ai_message)
                st.rerun()
                return

    except Exception as e:
        status_placeholder.empty()
        content_placeholder.empty()
        st.error(f"❌ 查询失败: {e}")


def handle_normal_query(api_client: APIClient, question: str, settings: dict):
    """普通查询"""

    with st.spinner("🤖 Agent正在处理..."):
        try:
            result = api_client.query(
                question,
                settings.get('session_id', 'default'),
                settings.get('top_k', 5)
            )

            # 构建消息
            ai_message = {
                "role": "assistant",
                "content": result.get("answer", ""),
                "tool_calls_count": result.get("tool_calls_count", 0)
            }

            # 如果有引用信息
            if result.get("sources"):
                ai_message["references"] = [
                    {"filename": src.get("source", "未知")}
                    for src in result["sources"][:3]
                ]

            st.session_state.messages.append(ai_message)
            st.rerun()

        except Exception as e:
            st.error(f"❌ 查询失败: {e}")


def has_knowledge_base_files(api_client: APIClient) -> bool:
    """检查是否有知识库文件"""
    try:
        stats = api_client.get_stats()
        return stats.get('total_files', 0) > 0
    except Exception:
        return False


def show_knowledge_base_hint():
    """显示知识库提示"""
    st.markdown("""
    <div style="padding: 1.5rem; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
               border-radius: 0.5rem; border-left: 4px solid #1976d2; margin: 1rem 0;">
        <h3 style="margin: 0 0 0.5rem 0; color: #1976d2;">💡 开始使用</h3>
        <p style="margin: 0; font-size: 0.9rem; color: #555;">
            请先切换到<strong>"📄 文档知识库"</strong>模块，上传医学文档并更新知识库，<br>
            然后回到这里开始智能问答。
        </p>
    </div>
    """, unsafe_allow_html=True)


def export_conversation():
    """导出对话记录"""
    if not st.session_state.messages:
        st.warning("暂无对话记录可导出")
        return

    try:
        # 构建导出文本
        export_text = f"# 对话记录\n\n"
        export_text += f"导出时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        export_text += "---\n\n"

        for msg in st.session_state.messages:
            role = "用户" if msg["role"] == "user" else "AI助手"
            export_text += f"**{role}:**\n\n{msg['content']}\n\n---\n\n"

        # 提供下载按钮
        st.download_button(
            label="📥 下载对话记录",
            data=export_text,
            file_name=f"conversation_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )

    except Exception as e:
        st.error(f"导出失败: {e}")
