"""文件项组件"""
import hashlib
import html
import re
from pathlib import Path

import docx2txt
import streamlit as st
from pypdf import PdfReader

from app.api_client import APIClient
from app.state_manager import state_manager

MAX_PREVIEW_CHARS = 4000
MAX_PREVIEW_PAGES = 3


def render_file_item(api_client: APIClient, file_info: dict):
    """渲染单个文件项"""
    filename = file_info.get('filename', '未知文件')
    filesize = file_info.get('size', 0)
    upload_time = file_info.get('upload_time', '')
    status = file_info.get('status', 'pending')
    filepath = file_info.get('filepath', '')
    source_id = file_info.get('source_id')
    version = file_info.get('version')
    category = file_info.get('category', 'general')
    is_current = file_info.get('is_current')
    widget_id = _build_file_widget_id(file_info)
    preview_key = _get_preview_state_key(widget_id)

    size_str = _format_file_size(filesize)
    status_info = _get_status_config(status)

    with st.expander(f"{status_info['icon']} {filename} ({size_str})"):
        col_info, col_actions = st.columns([3, 2])

        with col_info:
            _render_file_info(filename, size_str, upload_time, status_info, source_id, version, is_current)

        with col_actions:
            _render_file_actions(api_client, file_info, filepath, filename, status, category, preview_key, widget_id)

        if st.session_state.get(preview_key, False):
            _render_file_preview(file_info, widget_id)


def _build_file_widget_id(file_info: dict) -> str:
    """为 Streamlit widget 构建稳定且唯一的 id。

    说明：同名文件、同 source_id 的多版本等场景会导致仅使用 filename 的 key 冲突。
    这里将 source_id/version/filepath/filename 组合后做 md5，得到短且稳定的 key。
    """
    source_id = file_info.get("source_id")
    version = file_info.get("version")
    filepath = file_info.get("filepath", "")
    filename = file_info.get("filename", "unknown")
    raw = f"{source_id}|{version}|{filepath}|{filename}"
    return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


def _get_preview_state_key(widget_id: str) -> str:
    """构建预览开关状态键。"""
    return f"preview_visible_{widget_id}"


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
        'uploaded': {'label': '已上传待入库', 'color': '#999', 'icon': '⏳'},
        'processing': {'label': '更新中', 'color': '#1677ff', 'icon': '🔵'},
        'vectorized': {'label': '已向量化', 'color': '#52c41a', 'icon': '✅'},
        'active': {'label': '当前有效版本', 'color': '#52c41a', 'icon': '✅'},
        'superseded': {'label': '旧版本', 'color': '#faad14', 'icon': '🟠'},
        'failed': {'label': '失败', 'color': '#ff4d4f', 'icon': '❌'},
        'deleted': {'label': '已删除', 'color': '#999', 'icon': '🗑️'},
    }
    return status_config.get(status, status_config['pending'])


def _render_file_info(
    filename: str,
    size_str: str,
    upload_time: str,
    status_info: dict,
    source_id: str = None,
    version: int = None,
    is_current: bool = None,
):
    """渲染文件信息"""
    extra_lines = []
    if source_id:
        extra_lines.append(f"<p><strong>文件编号:</strong> <code>{source_id}</code></p>")
    if version is not None:
        current_text = "（当前生效）" if is_current else ""
        extra_lines.append(f"<p><strong>版本:</strong> 第 {version} 版 {current_text}</p>")

    st.markdown(f"""
    <div style="font-size: 0.85rem; color: #666;">
        <p><strong>文件名:</strong> {filename}</p>
        <p><strong>大小:</strong> {size_str}</p>
        <p><strong>上传时间:</strong> {upload_time}</p>
        <p><strong>状态:</strong> <span style="color: {status_info['color']};">{status_info['label']}</span></p>
        {''.join(extra_lines)}
    </div>
    """, unsafe_allow_html=True)


def _render_file_actions(
    api_client: APIClient,
    file_info: dict,
    filepath: str,
    filename: str,
    status: str,
    category: str,
    preview_key: str,
    widget_id: str,
):
    """渲染文件操作按钮"""
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    source_id = file_info.get("source_id")
    version = file_info.get("version")
    preview_visible = st.session_state.get(preview_key, False)
    preview_button_label = "🙈 收起预览" if preview_visible else "👁️ 查看预览"

    if st.button(preview_button_label, key=f"preview_btn_{widget_id}", use_container_width=True):
        st.session_state[preview_key] = not preview_visible
        st.rerun()

    _render_download_button(file_info, widget_id)

    if status in {'pending', 'uploaded', 'failed'}:
        if st.button("🔄 更新入库", key=f"update_btn_{widget_id}",
                     use_container_width=True, type="primary"):
            _handle_single_vectorization(api_client, filepath, category)

    if source_id:
        target_version = st.number_input(
            "回退到第几版",
            min_value=1,
            value=int(version or 1),
            step=1,
            key=f"rollback_version_{widget_id}",
        )
        if st.button("↩️ 回退版本", key=f"rollback_btn_{widget_id}", use_container_width=True):
            _handle_file_rollback(api_client, source_id, int(target_version), filename)

    if st.button("🗑️ 删除", key=f"delete_btn_{widget_id}", use_container_width=True):
        _handle_file_delete(api_client, file_info, filename)


@st.cache_data(show_spinner=False)
def _load_file_preview(filepath: str) -> dict:
    """读取文件预览内容。"""
    path = Path(filepath)
    if not path.exists():
        return {
            "success": False,
            "message": f"文件不存在：{filepath}",
            "content": "",
        }

    suffix = path.suffix.lower()

    try:
        if suffix == ".txt":
            full_content = path.read_text(encoding="utf-8", errors="ignore")
            return {
                "success": True,
                "content": full_content[:MAX_PREVIEW_CHARS],
                "truncated": len(full_content) > MAX_PREVIEW_CHARS,
                "summary": "文本文件预览",
                "file_type": "txt",
            }

        if suffix == ".docx":
            full_content = docx2txt.process(str(path)) or ""
            return {
                "success": True,
                "content": full_content[:MAX_PREVIEW_CHARS],
                "truncated": len(full_content) > MAX_PREVIEW_CHARS,
                "summary": "Word 文档正文预览",
                "file_type": "docx",
            }

        if suffix == ".pdf":
            reader = PdfReader(str(path))
            pages = []
            for page_index, page in enumerate(reader.pages[:MAX_PREVIEW_PAGES], start=1):
                page_text = page.extract_text() or ""
                pages.append({
                    "page": page_index,
                    "content": page_text[:MAX_PREVIEW_CHARS],
                    "truncated": len(page_text) > MAX_PREVIEW_CHARS,
                })
            full_content = "\n\n".join(page["content"] for page in pages)
            return {
                "success": True,
                "content": full_content[:MAX_PREVIEW_CHARS],
                "truncated": len(full_content) > MAX_PREVIEW_CHARS,
                "summary": f"PDF 前 {min(len(reader.pages), MAX_PREVIEW_PAGES)} 页文字预览（共 {len(reader.pages)} 页）",
                "pages": pages,
                "total_pages": len(reader.pages),
                "file_type": "pdf",
            }

        return {
            "success": False,
            "message": f"暂不支持预览此文件类型：{suffix}",
            "content": "",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"读取预览失败：{e}",
            "content": "",
        }


def _highlight_preview_text(content: str, keyword: str) -> str:
    """对预览文本做简单关键词高亮。"""
    escaped_content = html.escape(content)
    if not keyword:
        return escaped_content.replace("\n", "<br>")

    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    highlighted = pattern.sub(
        lambda match: f"<mark style='background:#fff3a3;padding:0 2px;'>{html.escape(match.group(0))}</mark>",
        escaped_content
    )
    return highlighted.replace("\n", "<br>")


def _render_download_button(file_info: dict, widget_id: str):
    """渲染原文件下载按钮。"""
    filepath = file_info.get("filepath", "")
    filename = file_info.get("filename", "download")
    path = Path(filepath)
    if not path.exists():
        return

    try:
        with open(path, "rb") as file_obj:
            st.download_button(
                "⬇️ 下载原文件",
                data=file_obj.read(),
                file_name=filename,
                mime="application/octet-stream",
                key=f"download_btn_{widget_id}",
                use_container_width=True,
            )
    except Exception as e:
        st.caption(f"下载按钮暂不可用：{e}")


def _render_text_preview(content: str, truncated: bool, widget_id: str):
    """渲染文本类文件预览。"""
    keyword = st.text_input(
        "高亮关键词",
        placeholder="输入关键词后将在预览中高亮显示",
        key=f"preview_keyword_{widget_id}",
    )
    highlighted_html = _highlight_preview_text(content, keyword.strip())
    st.markdown(
        f"""
        <div style="padding: 0.75rem; background: #fafafa; border: 1px solid #eee; border-radius: 0.5rem;
                    max-height: 420px; overflow-y: auto; line-height: 1.65; font-size: 0.92rem;">
            {highlighted_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if truncated:
        st.caption("预览内容已截断，仅显示前面的部分文本。")


def _render_pdf_preview(preview: dict, widget_id: str):
    """渲染 PDF 分页预览。"""
    pages = preview.get("pages", [])
    if not pages:
        st.info("未能提取到 PDF 文本内容。")
        return

    page_options = [page["page"] for page in pages]
    selected_page = st.selectbox(
        "选择预览页码",
        page_options,
        key=f"pdf_preview_page_{widget_id}",
    )
    page_data = next((page for page in pages if page["page"] == selected_page), pages[0])
    _render_text_preview(page_data.get("content", ""), page_data.get("truncated", False), widget_id)

    total_pages = preview.get("total_pages")
    if total_pages:
        st.caption(f"当前仅预览前 {len(pages)} 页，可用于快速查看文档内容。整份 PDF 共 {total_pages} 页。")


def _render_file_preview(file_info: dict, widget_id: str):
    """渲染文件预览区域"""
    filename = file_info.get('filename', '')
    filepath = file_info.get('filepath', '')
    preview = _load_file_preview(filepath)

    st.divider()
    st.markdown("**文件预览**")
    st.caption(f"文件：{filename}")
    st.caption(f"路径：{filepath}")

    if not preview.get("success", False):
        st.warning(preview.get("message", "暂时无法预览该文件"))
        return

    st.caption(preview.get("summary", "文件内容预览"))
    content = (preview.get("content") or "").strip()
    if not content:
        st.info("已成功读取文件，但暂时没有可展示的文本内容。")
        return

    if preview.get("file_type") == "pdf":
        _render_pdf_preview(preview, widget_id)
        return

    _render_text_preview(content, preview.get("truncated", False), widget_id)


def _handle_single_vectorization(api_client: APIClient, filepath: str, category: str):
    """处理单个文件向量化"""
    import time
    try:
        with st.spinner(f"🔄 正在向量化..."):
            result = api_client.ingest_file(filepath, category)

            st.success(f"✅ 导入成功: {result.get('ingested_count', 0)} 个文档块")
            state_manager.add_operation_log(
                f"更新入库: {filepath.split('/')[-1]}",
                f"✅ 导入 {result.get('ingested_count', 0)} 个文档块",
                True
            )

            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 向量化失败: {e}")
        state_manager.add_operation_log(
            f"更新入库: {filepath.split('/')[-1]}",
            f"❌ 失败: {str(e)}",
            False
        )


def _handle_file_delete(api_client: APIClient, filepath: str, filename: str):
    """处理文件删除"""
    import time
    try:
        source_id = filepath.get("source_id") if isinstance(filepath, dict) else None
        category = filepath.get("category", "general") if isinstance(filepath, dict) else "general"
        source_name = filepath.get("filename", filename) if isinstance(filepath, dict) else filename

        if source_id:
            result = api_client.delete_by_rule(source_id=source_id)
        else:
            result = api_client.delete_by_rule(category=category, source=source_name)

        if not result.get("success", False):
            raise RuntimeError(result.get("message", "删除失败"))

        st.success(f"✅ {result.get('message', f'文件 {filename} 已删除')}")
        state_manager.add_operation_log(
            f"删除文件: {filename}",
            f"✅ {result.get('message', '删除成功')}",
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


def _handle_file_rollback(api_client: APIClient, source_id: str, target_version: int, filename: str):
    """处理文件版本回滚"""
    import time
    try:
        with st.spinner(f"↩️ 正在将 {filename} 回退到第 {target_version} 版..."):
            result = api_client.rollback_document(source_id, target_version)
            if not result.get("success", False):
                raise RuntimeError(result.get("message", "回滚失败"))

            st.success(f"✅ {result.get('message', '回滚成功')}")
            state_manager.add_operation_log(
                f"回滚文件: {filename}",
                f"✅ {result.get('message', '回滚成功')}",
                True
            )
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"❌ 回滚失败: {e}")
        state_manager.add_operation_log(
            f"回滚文件: {filename}",
            f"❌ 失败: {str(e)}",
            False
        )
