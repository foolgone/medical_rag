"""文件项组件"""
import streamlit as st
from app.api_client import APIClient
from app.state_manager import state_manager


def render_file_item(api_client: APIClient, file_info: dict):
    """渲染单个文件项"""
    filename = file_info.get('filename', '未知文件')
    filesize = file_info.get('size', 0)
    upload_time = file_info.get('upload_time', '')
    status = file_info.get('status', 'pending')
    filepath = file_info.get('filepath', '')

    size_str = _format_file_size(filesize)
    status_info = _get_status_config(status)

    with st.expander(f"{status_info['icon']} {filename} ({size_str})"):
        col_info, col_actions = st.columns([3, 2])

        with col_info:
            _render_file_info(filename, size_str, upload_time, status_info)

        with col_actions:
            _render_file_actions(api_client, file_info, filepath, filename, status)


def _format_file_size(filesize: int) -> str:
    """格式化文件大小"""
    if filesize < 1024:
        return f"{filesize} B"
    elif filesize < 1024 * 1024:
        return f"{filesize / 1024:.1f} KB"
    else:
        return f"{filesize / (1024 * 1024):.1f} MB"


def _get_status_config(status: str) -> dict:
    """获取状态配置"""
    status_config = {
        'pending': {'label': '未向量化', 'color': '#999', 'icon': '⚪'},
        'processing': {'label': '更新中', 'color': '#1677ff', 'icon': '🔵'},
        'vectorized': {'label': '已向量化', 'color': '#52c41a', 'icon': '✅'},
        'failed': {'label': '失败', 'color': '#ff4d4f', 'icon': '❌'}
    }
    return status_config.get(status, status_config['pending'])


def _render_file_info(filename: str, size_str: str, upload_time: str, status_info: dict):
    """渲染文件信息"""
    st.markdown(f"""
    <div style="font-size: 0.85rem; color: #666;">
        <p><strong>文件名:</strong> {filename}</p>
        <p><strong>大小:</strong> {size_str}</p>
        <p><strong>上传时间:</strong> {upload_time}</p>
        <p><strong>状态:</strong> <span style="color: {status_info['color']};">{status_info['label']}</span></p>
    </div>
    """, unsafe_allow_html=True)


def _render_file_actions(api_client: APIClient, file_info: dict, filepath: str, filename: str, status: str):
    """渲染文件操作按钮"""
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

    if st.button("👁️ 预览", key=f"preview_{filename}", use_container_width=True):
        _handle_file_preview(file_info)

    if status == 'pending' or status == 'failed':
        if st.button("🔄 单独更新", key=f"update_{filename}",
                     use_container_width=True, type="primary"):
            _handle_single_vectorization(api_client, filepath, file_info.get('category', 'general'))

    if st.button("🗑️ 删除", key=f"delete_{filename}", use_container_width=True):
        if st.warning(f"确定删除文件 '{filename}' 吗？"):
            if st.button("✅ 确认删除", key=f"confirm_delete_{filename}",
                         type="primary", use_container_width=True):
                _handle_file_delete(api_client, filepath, filename)


def _handle_file_preview(file_info: dict):
    """处理文件预览"""
    filename = file_info.get('filename', '')
    filepath = file_info.get('filepath', '')
    st.info(f"预览功能开发中: {filename}")
    st.caption(f"文件路径: {filepath}")


def _handle_single_vectorization(api_client: APIClient, filepath: str, category: str):
    """处理单个文件向量化"""
    import time
    try:
        with st.spinner(f"🔄 正在向量化..."):
            result = api_client.ingest_file(filepath, category)

            st.success(f"✅ 导入成功: {result.get('ingested_count', 0)} 个文档块")
            state_manager.add_operation_log(
                f"单独更新: {filepath.split('/')[-1]}",
                f"✅ 导入 {result.get('ingested_count', 0)} 个文档块",
                True
            )

            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 向量化失败: {e}")
        state_manager.add_operation_log(
            f"单独更新: {filepath.split('/')[-1]}",
            f"❌ 失败: {str(e)}",
            False
        )


def _handle_file_delete(api_client: APIClient, filepath: str, filename: str):
    """处理文件删除"""
    import time
    try:
        st.success(f"✅ 文件 '{filename}' 已删除")
        state_manager.add_operation_log(
            f"删除文件: {filename}",
            "✅ 删除成功",
            True
        )
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"❌ 删除失败: {e}")
        state_manager.add_operation_log(
            f"删除文件: {filename}",
            f"❌ 失败: {str(e)}",
            False
        )
