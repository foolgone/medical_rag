"""医疗Agent问答系统 - Streamlit前端（重构版）"""
import streamlit as st
from app.config import AppConfig
from app.api_client import APIClient
from app.state_manager import state_manager
from app.styles import style_manager
from app.components.navigation import NavigationComponent
from app.pages.chat_page import ChatPage
from app.pages.knowledge_page import KnowledgePage
from app.pages.settings_page import SettingsPage


def main():
    """主函数"""
    # 初始化配置和客户端
    config = AppConfig()
    api_client = APIClient(config)

    # 初始化状态管理器
    state_manager.initialize()

    # 页面配置
    st.set_page_config(
        page_title=config.page_title,
        page_icon=config.page_icon,
        layout="wide"
    )

    # 应用全局样式
    st.markdown(style_manager.get_global_styles(), unsafe_allow_html=True)

    # 渲染标题
    st.markdown('<h1 class="main-header">🏥 医疗Agent问答系统</h1>', unsafe_allow_html=True)

    # 渲染导航栏
    navigation = NavigationComponent(api_client)
    navigation.render()

    # 页面路由
    pages = {
        "chat": ChatPage(api_client, config),
        "knowledge": KnowledgePage(api_client, config),
        "settings": SettingsPage(api_client, config)
    }

    current_page = state_manager.current_page
    page = pages.get(current_page, pages["chat"])
    page.render()

    # 底部说明
    render_footer()


def render_footer():
    """渲染页脚"""
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.85rem; padding: 1rem 0;'>
        <p style="margin: 0.3rem 0;">🏥 医疗Agent问答系统 v2.0 | 基于LangGraph Tool Calling Agent + Ollama + PostgreSQL</p>
        <p style="margin: 0.3rem 0;">⚠️ 免责声明：本系统仅供参考，不能替代专业医疗建议</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
