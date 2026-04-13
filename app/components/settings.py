"""系统设置模块 - API配置、RAG检索配置、系统基础配置"""
import streamlit as st
from app.api_client import APIClient
from app.config import AppConfig


def render_settings_module(api_client: APIClient, config: AppConfig):
    """渲染系统设置模块"""

    st.markdown("""
    <div style="padding: 1rem; background: #f0f9ff; border-radius: 0.5rem; margin-bottom: 1.5rem;">
        <p style="margin: 0; font-size: 0.9rem; color: #666;">
            ⚙️ 配置系统参数，修改后请点击"保存设置"生效
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 分组1: API配置
    render_api_settings(api_client, config)

    st.divider()

    # 分组2: RAG检索配置
    render_rag_settings(config)

    st.divider()

    # 分组3: 系统基础配置
    render_system_settings(config)

    st.divider()

    # 保存和重置按钮
    render_settings_actions()


def render_api_settings(api_client: APIClient, config: AppConfig):
    """分组1: API配置"""
    st.subheader("🔌 API配置")

    col1, col2 = st.columns([3, 1])

    with col1:
        # API地址
        api_url = st.text_input(
            "API地址",
            value=config.api_base_url,
            key="setting_api_url",
            help="后端FastAPI服务地址"
        )

        # 会话ID
        if 'session_id' not in st.session_state:
            from datetime import datetime
            st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        session_id = st.text_input(
            "会话ID",
            value=st.session_state.session_id,
            key="setting_session_id",
            help="用于区分不同对话会话"
        )

        # 超时时间
        timeout = st.number_input(
            "接口超时时间（秒）",
            min_value=10,
            max_value=300,
            value=config.timeout,
            step=10,
            key="setting_timeout",
            help="请求超时的最大等待时间"
        )

    with col2:
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

        # 测试连接按钮
        if st.button("🔍 测试连接", use_container_width=True, type="secondary"):
            test_api_connection(api_url)


def render_rag_settings(config: AppConfig):
    """分组2: RAG检索配置"""
    st.subheader("🔍 RAG检索配置")

    # 检索文档数量
    top_k = st.slider(
        "检索文档数量",
        min_value=1,
        max_value=10,
        value=config.default_top_k,
        step=1,
        key="setting_top_k",
        help="每次检索返回的相关文档数量。数量越多，回复越全面，但速度可能变慢"
    )
    st.caption("💡 建议值：3-7个，平衡准确性和速度")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    st.selectbox(
        "问答模式",
        ["agent", "rag"],
        index=["agent", "rag"].index(st.session_state.get("query_mode", "agent")),
        key="setting_query_mode",
        help="agent 会自动调用工具；rag 只走知识库检索增强生成"
    )

    st.caption("💡 如果你更想要稳定的知识库直答，可切到 rag；如果你需要工具能力，选 agent")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    query_category = st.selectbox(
        "问答检索分类",
        ["all", "general", "cardiology", "endocrinology", "neurology", "other"],
        index=["all", "general", "cardiology", "endocrinology", "neurology", "other"].index(
            st.session_state.get("query_category", "all")
        ),
        key="setting_query_category",
        help="限制问答仅检索指定分类；all 表示不过滤"
    )

    st.caption("💡 如果你只想在某一类医学文档里检索，可以先在这里限制范围")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # 向量化阈值
    similarity_threshold = st.slider(
        "相似度阈值",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        key="setting_similarity_threshold",
        help="文档相似度低于此阈值的将被过滤掉"
    )
    st.caption("💡 建议值：0.6-0.8，越高越严格")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # 流式输出
    enable_streaming = st.checkbox(
        "✨ 启用流式输出",
        value=True,
        key="setting_enable_streaming",
        help="实时显示AI回复内容，提升用户体验"
    )

    # 显示工具调用
    show_tool_calls = st.checkbox(
        "🔧 显示工具调用信息",
        value=True,
        key="setting_show_tool_calls",
        help="在对话中显示Agent调用的工具名称"
    )


def render_system_settings(config: AppConfig):
    """分组3: 系统基础配置"""
    st.subheader("🎨 系统基础配置")

    # 主题切换
    theme = st.selectbox(
        "主题模式",
        ["浅色模式", "深色模式"],
        index=0,
        key="setting_theme",
        help="切换界面主题"
    )

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # 消息提醒
    enable_notifications = st.checkbox(
        "🔔 开启消息提醒",
        value=True,
        key="setting_notifications",
        help="上传、更新等操作完成后显示弹窗提示"
    )

    # 自动保存配置
    auto_save = st.checkbox(
        "💾 自动保存配置",
        value=True,
        key="setting_auto_save",
        help="修改配置后自动保存，无需手动点击"
    )


def render_settings_actions():
    """保存和重置按钮"""
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 保存设置", type="primary", use_container_width=True):
            save_settings()

    with col2:
        if st.button("🔄 恢复默认", use_container_width=True):
            reset_to_defaults()

    with col3:
        st.caption("💡 修改配置后记得点击\"保存设置\"")


def test_api_connection(api_url: str):
    """测试API连接"""
    try:
        import requests
        response = requests.get(f"{api_url}/stats", timeout=5)

        if response.status_code == 200:
            st.success("✅ 连接成功！")
        else:
            st.error(f"❌ 连接失败: HTTP {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error("❌ 无法连接到服务器，请检查API地址是否正确")
    except requests.exceptions.Timeout:
        st.error("❌ 连接超时，请检查网络或服务器状态")
    except Exception as e:
        st.error(f"❌ 连接失败: {str(e)}")


def save_settings():
    """保存设置"""
    try:
        # 更新会话状态
        if 'setting_api_url' in st.session_state:
            st.session_state.api_url = st.session_state.setting_api_url

        if 'setting_session_id' in st.session_state:
            st.session_state.session_id = st.session_state.setting_session_id

        if 'setting_top_k' in st.session_state:
            st.session_state.top_k = st.session_state.setting_top_k

        if 'setting_query_category' in st.session_state:
            st.session_state.query_category = st.session_state.setting_query_category

        if 'setting_query_mode' in st.session_state:
            st.session_state.query_mode = st.session_state.setting_query_mode

        if 'setting_enable_streaming' in st.session_state:
            st.session_state.enable_streaming = st.session_state.setting_enable_streaming

        if 'setting_show_tool_calls' in st.session_state:
            st.session_state.show_tool_calls = st.session_state.setting_show_tool_calls

        st.success("✅ 设置已保存！")

        # 延迟刷新
        import time
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"❌ 保存失败: {e}")


def reset_to_defaults():
    """恢复默认设置"""
    if st.warning("⚠️ 确定要恢复所有设置为默认值吗？"):
        if st.button("✅ 确认恢复", type="primary"):
            # 清除自定义设置
            keys_to_clear = [
                'setting_api_url', 'setting_session_id', 'setting_top_k', 'setting_query_category', 'setting_query_mode',
                'setting_enable_streaming', 'setting_show_tool_calls'
            ]

            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            st.success("✅ 已恢复默认设置")
            import time
            time.sleep(1)
            st.rerun()
