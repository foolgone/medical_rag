"""医疗Agent问答系统 - Streamlit前端（优化版）"""
import streamlit as st
from app.config import AppConfig
from app.api_client import APIClient
from app.components.chat_area import render_chat_area
from app.components.knowledge_base import render_knowledge_base_module
from app.components.settings import render_settings_module


def render_navigation():
    """渲染侧边栏导航"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #1677ff; margin: 0;">🏥 医疗Agent</h2>
            <p style="color: #666; font-size: 0.85rem; margin: 0.5rem 0 0 0;">智能问答系统 v2.0</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # 导航按钮
        nav_chat = st.button(
            "💬 聊天对话",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "chat" else "secondary",
            key="nav_chat"
        )

        nav_kb = st.button(
            "📄 文档知识库",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "knowledge" else "secondary",
            key="nav_kb"
        )

        nav_settings = st.button(
            "⚙️ 系统设置",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "settings" else "secondary",
            key="nav_settings"
        )

        # 更新导航状态
        if nav_chat:
            st.session_state.current_page = "chat"
            st.rerun()
        elif nav_kb:
            st.session_state.current_page = "knowledge"
            st.rerun()
        elif nav_settings:
            st.session_state.current_page = "settings"
            st.rerun()

        st.divider()

        # 快速统计
        try:
            stats = api_client.get_stats()
            st.markdown(f"""
            <div style="padding: 0.8rem; background: white; border-radius: 0.5rem; 
                       box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <p style="margin: 0; font-size: 0.8rem; color: #666;">
                    📊 <strong>知识库概览</strong><br>
                    文件数: {stats.get('total_files', 0)}<br>
                    已向量化: {stats.get('vectorized_files', 0)}
                </p>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            st.info("📊 连接后端查看统计")


def render_chat_page(api_client: APIClient, config: AppConfig):
    """渲染聊天对话页面"""

    # 初始化消息列表
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # 从设置中获取配置
    settings = {
        'api_url': st.session_state.get('api_url', config.api_base_url),
        'session_id': st.session_state.get('session_id', f"session_default"),
        'top_k': st.session_state.get('top_k', config.default_top_k),
        'enable_streaming': st.session_state.get('enable_streaming', True),
        'show_tool_calls': st.session_state.get('show_tool_calls', True)
    }

    # 渲染聊天区域
    render_chat_area(api_client, settings)


def render_knowledge_page(api_client: APIClient):
    """渲染文档知识库页面"""
    render_knowledge_base_module(api_client)


def render_settings_page(api_client: APIClient, config: AppConfig):
    """渲染系统设置页面"""
    render_settings_module(api_client, config)


# 页面配置
config = AppConfig()
st.set_page_config(page_title=config.page_title, page_icon=config.page_icon, layout="wide")

# 自定义CSS
st.markdown("""
<style>
    /* 全局样式 */
    .main-header {
        font-size: 2.2rem;
        font-weight: 600;
        background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fafafa 0%, #f5f5f5 100%);
    }
    
    /* 按钮悬停效果 */
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
    }
    
    /* 卡片阴影 */
    div[data-testid="stExpander"] {
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<h1 class="main-header">🏥 医疗Agent问答系统</h1>', unsafe_allow_html=True)

# 初始化API客户端
api_client = APIClient(config)

# 初始化导航状态
if 'current_page' not in st.session_state:
    st.session_state.current_page = "chat"

# 渲染侧边栏导航
render_navigation()

# 根据导航显示对应页面
if st.session_state.current_page == "chat":
    render_chat_page(api_client, config)
elif st.session_state.current_page == "knowledge":
    render_knowledge_page(api_client)
elif st.session_state.current_page == "settings":
    render_settings_page(api_client, config)


# 底部说明
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85rem; padding: 1rem 0;'>
    <p style="margin: 0.3rem 0;">🏥 医疗Agent问答系统 v2.0 | 基于LangGraph Tool Calling Agent + Ollama + PostgreSQL</p>
    <p style="margin: 0.3rem 0;">⚠️ 免责声明：本系统仅供参考，不能替代专业医疗建议</p>
</div>
""", unsafe_allow_html=True)

