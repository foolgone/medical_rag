"""文件列表组件"""
import streamlit as st
from app.api_client import APIClient
from app.components.knowledge_base.file_item import render_file_item


# 每页显示的文件数
FILES_PER_PAGE = 10


def render_file_list(api_client: APIClient):
    """渲染文件列表（分页显示以提升性能）"""
    st.subheader("📄 文件列表")

    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_keyword = st.text_input("🔍 搜索文件", placeholder="按文件名搜索...", key="file_search")
    with col_filter:
        filter_status = st.selectbox(
            "筛选状态",
            ["全部", "未向量化", "已向量化", "更新中", "失败"],
            key="file_filter"
        )

    try:
        files_data = api_client.list_files()
        files = files_data.get('files', [])

        files = _apply_filters(files, search_keyword, filter_status)

        if not files:
            st.info("暂无文件，请先上传文件")
            return

        st.caption(f"共 {len(files)} 个文件")

        # 分页显示
        total_pages = (len(files) + FILES_PER_PAGE - 1) // FILES_PER_PAGE

        if total_pages > 1:
            page = st.selectbox(
                "选择页码",
                range(1, total_pages + 1),
                key="file_list_page"
            )
            start_idx = (page - 1) * FILES_PER_PAGE
            end_idx = start_idx + FILES_PER_PAGE
            files_to_display = files[start_idx:end_idx]
        else:
            files_to_display = files

        for file_info in files_to_display:
            render_file_item(api_client, file_info)

    except Exception as e:
        st.error(f"❌ 获取文件列表失败: {e}")


def _apply_filters(files: list, search_keyword: str, filter_status: str) -> list:
    """应用筛选条件"""
    if search_keyword:
        files = [f for f in files if search_keyword.lower() in f.get('filename', '').lower()]

    if filter_status != "全部":
        status_map = {
            "未向量化": {"pending", "uploaded"},
            "已向量化": {"vectorized", "active"},
            "更新中": "processing",
            "失败": "failed"
        }
        target_status = status_map.get(filter_status, "")
        if isinstance(target_status, set):
            files = [f for f in files if f.get('status') in target_status]
        else:
            files = [f for f in files if f.get('status') == target_status]

    return files

