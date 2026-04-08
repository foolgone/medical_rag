"""
医疗RAG问答系统 - Streamlit前端界面（流式输出版）
"""
import streamlit as st
import requests
import json
import time
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="医疗RAG问答系统",
    page_icon="🏥",
    layout="wide"
)

# API基础URL
API_BASE_URL = "http://localhost:8000/api/v1"

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .bot-message {
        background-color: #f5f5f5;
        border-left: 4px solid #4caf50;
    }
    .source-box {
        background-color: #fff3e0;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }
    .streaming-cursor::after {
        content: '▋';
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<h1 class="main-header">🏥 医疗RAG问答系统</h1>', unsafe_allow_html=True)

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 设置")

    # API地址配置
    api_url = st.text_input("API地址", value=API_BASE_URL)

    # 会话ID
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_id = st.text_input("会话ID", value=st.session_state.session_id)

    # 检索参数
    top_k = st.slider("检索文档数量 (Top-K)", min_value=1, max_value=10, value=5)
    
    # 启用流式输出
    enable_streaming = st.checkbox("✨ 启用流式输出", value=True)

    st.divider()

    # 功能按钮
    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.rerun()

    if st.button("📊 查看统计"):
        try:
            response = requests.get(f"{api_url}/stats")
            if response.status_code == 200:
                stats = response.json()
                st.json(stats)
            else:
                st.error("获取统计信息失败")
        except Exception as e:
            st.error(f"错误: {str(e)}")

    st.divider()
    st.info("💡 提示：确保后端服务已启动在 http://localhost:8000")

# 初始化会话状态
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 显示聊天历史
chat_container = st.container()
with chat_container:
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            st.markdown(f'''
            <div class="chat-message user-message">
                <strong>👤 用户:</strong><br>
                {message["content"]}
            </div>
            ''', unsafe_allow_html=True)
        else:
            sources_html = ""
            if message.get("sources"):
                sources_html = "<div class='source-box'><strong>📚 参考来源:</strong><ul>"
                for source in message["sources"]:
                    sources_html += f"<li>{source.get('source', '未知')}</li>"
                sources_html += "</ul></div>"

            st.markdown(f'''
            <div class="chat-message bot-message">
                <strong>🤖 AI助手:</strong><br>
                {message["content"]}
                {sources_html}
            </div>
            ''', unsafe_allow_html=True)

# 输入区域
st.divider()
question = st.chat_input("请输入您的医疗问题...")

if question:
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": question})
    
    if enable_streaming:
        # ========== 流式输出模式 ==========
        # 创建一个空的AI助手消息占位符
        assistant_placeholder = st.empty()
        assistant_content = ""
        sources = []
        
        try:
            # 调用流式API
            response = requests.post(
                f"{api_url}/query-stream",
                json={
                    "question": question,
                    "session_id": session_id,
                    "k": top_k
                },
                stream=True,
                timeout=120,
                headers={"Accept": "text/event-stream"}
            )
            
            if response.status_code == 200:
                # 逐行读取SSE数据
                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data: "):
                        # 解析JSON数据
                        data_str = line[6:]  # 去掉 "data: " 前缀
                        try:
                            data = json.loads(data_str)
                            event_type = data.get("type")
                            
                            if event_type == "start":
                                # 开始信号
                                assistant_content = "🔍 正在思考..."
                                assistant_placeholder.markdown(f'''
                                <div class="chat-message bot-message">
                                    <strong>🤖 AI助手:</strong><br>
                                    <span class="streaming-cursor">{assistant_content}</span>
                                </div>
                                ''', unsafe_allow_html=True)
                                
                            elif event_type == "sources":
                                # 接收检索结果
                                sources = data.get("sources", [])
                                count = data.get("count", 0)
                                if count > 0:
                                    assistant_content = f"📚 已找到 {count} 个相关文档，正在生成回答...\n\n"
                                else:
                                    assistant_content = "💬 未找到相关文档，将直接回答...\n\n"
                                
                            elif event_type == "content":
                                # 接收内容片段
                                chunk = data.get("content", "")
                                assistant_content += chunk
                                
                                # 更新显示
                                sources_html = ""
                                if sources:
                                    sources_html = "<div class='source-box'><strong>📚 参考来源:</strong><ul>"
                                    for source in sources:
                                        sources_html += f"<li>{source.get('source', '未知')}</li>"
                                    sources_html += "</ul></div>"
                                
                                assistant_placeholder.markdown(f'''
                                <div class="chat-message bot-message">
                                    <strong>🤖 AI助手:</strong><br>
                                    <span class="streaming-cursor">{assistant_content}</span>
                                    {sources_html}
                                </div>
                                ''', unsafe_allow_html=True)
                                
                            elif event_type == "end":
                                # 完成信号 - 移除光标动画
                                sources_html = ""
                                if sources:
                                    sources_html = "<div class='source-box'><strong>📚 参考来源:</strong><ul>"
                                    for source in sources:
                                        sources_html += f"<li>{source.get('source', '未知')}</li>"
                                    sources_html += "</ul></div>"
                                
                                assistant_placeholder.markdown(f'''
                                <div class="chat-message bot-message">
                                    <strong>🤖 AI助手:</strong><br>
                                    {assistant_content}
                                    {sources_html}
                                </div>
                                ''', unsafe_allow_html=True)
                                
                                # 保存到会话状态
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": assistant_content,
                                    "sources": sources
                                })
                                break
                                
                            elif event_type == "error":
                                error_msg = data.get("error", "未知错误")
                                assistant_placeholder.markdown(f'''
                                <div class="chat-message bot-message">
                                    <strong>🤖 AI助手:</strong><br>
                                    ❌ 流式输出错误: {error_msg}
                                </div>
                                ''', unsafe_allow_html=True)
                                break
                                
                        except json.JSONDecodeError as e:
                            continue
                            
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ API错误: {response.status_code}",
                    "sources": []
                })
                
        except requests.exceptions.ConnectionError:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "❌ 无法连接到后端服务，请确保服务已启动",
                "sources": []
            })
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ 请求失败: {str(e)}",
                "sources": []
            })
        
        st.rerun()
        
    else:
        # ========== 非流式输出模式（原有逻辑） ==========
        with st.spinner("🔍 正在检索相关医疗文档..."):
            try:
                # 调用后端API
                response = requests.post(
                    f"{api_url}/query",
                    json={
                        "question": question,
                        "session_id": session_id,
                        "k": top_k
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("answer", "抱歉，我无法回答这个问题。")
                    sources = result.get("sources", [])

                    # 显示AI回答
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                    st.rerun()
                else:
                    error_msg = f"API错误: {response.status_code} - {response.text}"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ {error_msg}",
                        "sources": []
                    })
                    st.rerun()

            except requests.exceptions.ConnectionError:
                error_msg = "无法连接到后端服务，请确保服务已启动"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ {error_msg}",
                    "sources": []
                })
                st.rerun()
            except Exception as e:
                error_msg = f"请求失败: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ {error_msg}",
                    "sources": []
                })
                st.rerun()

# 底部说明
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>🏥 医疗RAG问答系统 v1.0 | 基于LangChain + Ollama + PostgreSQL</p>
    <p>⚠️ 免责声明：本系统仅供参考，不能替代专业医疗建议</p>
</div>
""", unsafe_allow_html=True)
