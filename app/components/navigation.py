"""导航组件 - 侧边栏导航"""
import streamlit as st
from app.state_manager import state_manager
from app.api_client import APIClient


@st.cache_data(ttl=30)
def get_cached_stats(api_base_url: str):
    """缓存统计信息，30秒过期"""
    try:
        import requests
        response = requests.get(f"{api_base_url}/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


class NavigationComponent:
    """导航组件"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def render(self):
        """渲染导航栏"""
        with st.sidebar:
            self._render_header()
            st.divider()
            self._render_nav_buttons()
            st.divider()
            self._render_stats()

    def _render_header(self):
        """渲染头部"""
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #1677ff; margin: 0;">🏥 医疗Agent</h2>
            <p style="color: #666; font-size: 0.85rem; margin: 0.5rem 0 0 0;">智能问答系统 v2.0</p>
        </div>
        """, unsafe_allow_html=True)

    def _render_nav_buttons(self):
        """渲染导航按钮"""
        nav_items = [
            ("chat", "💬 聊天对话"),
            ("knowledge", "📄 文档知识库"),
            ("settings", "⚙️ 系统设置")
        ]

        for page_key, label in nav_items:
            is_active = state_manager.current_page == page_key
            button_type = "primary" if is_active else "secondary"

            if st.button(label, use_container_width=True, type=button_type, key=f"nav_{page_key}"):
                state_manager.current_page = page_key
                st.rerun()

    def _render_stats(self):
        """渲染统计信息（使用缓存）"""
        try:
            stats = get_cached_stats(self.api_client.config.api_base_url)
            if stats:
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
            else:
                st.info("📊 连接后端查看统计")
        except Exception:
            st.info("📊 连接后端查看统计")

