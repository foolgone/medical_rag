"""知识库主容器组件"""
import streamlit as st
from app.api_client import APIClient
from app.components.knowledge_base.file_upload import render_file_upload
from app.components.knowledge_base.kb_operations import render_kb_operations
from app.components.knowledge_base.file_list import render_file_list
from app.components.knowledge_base.kb_logs import render_kb_logs


def render_knowledge_base_module(api_client: APIClient):
    """渲染知识库模块"""
    if 'kb_refresh' not in st.session_state:
        st.session_state.kb_refresh = 0

    col1, col2 = st.columns([2, 1])

    with col1:
        render_file_upload(api_client)

    with col2:
        render_kb_operations(api_client)

    st.divider()

    render_file_list(api_client)

    st.divider()

    render_kb_logs()

