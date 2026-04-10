"""文件上传组件"""
import streamlit as st
import time
from app.api_client import APIClient
from app.state_manager import state_manager


def render_file_upload(api_client: APIClient):
    """渲染文件上传区域"""
    st.subheader("📤 文件上传")

    category = st.selectbox(
        "文档分类",
        ["general", "cardiology", "endocrinology", "neurology", "other"],
        key="upload_category"
    )

    uploaded_files = st.file_uploader(
        "选择文件上传（支持多文件）",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="支持PDF、DOCX、TXT格式，可同时上传多个文件"
    )

    if uploaded_files:
        st.info(f"已选择 {len(uploaded_files)} 个文件")
        _render_upload_buttons(api_client, uploaded_files, category)


def _render_upload_buttons(api_client: APIClient, uploaded_files, category: str):
    """渲染上传按钮"""
    col_upload, col_clear = st.columns([1, 1])

    with col_upload:
        if st.button("📥 开始上传", type="primary", use_container_width=True):
            handle_file_upload(api_client, uploaded_files, category)

    with col_clear:
        if st.button("🗑️ 清除选择", use_container_width=True):
            st.rerun()


def handle_file_upload(api_client: APIClient, files, category: str):
    """处理文件上传（优化进度显示）"""
    progress_bar = st.progress(0)
    status_text = st.empty()

    success_count = 0
    fail_count = 0

    try:
        total = len(files)

        for i, uploaded_file in enumerate(files):
            # 简化状态文本，减少渲染
            status_text.text(f"上传中 {i + 1}/{total}")

            try:
                result = api_client.upload_file(uploaded_file, category)
                ingest_result = api_client.ingest_file(result['filepath'], category)

                success_count += 1
                # 减少日志记录频率
                if i == total - 1:  # 只记录最后一次
                    state_manager.add_operation_log(
                        f"上传文件: {uploaded_file.name}",
                        f"✅ 成功导入 {ingest_result.get('ingested_count', 0)} 个文档块",
                        True
                    )

            except Exception as e:
                fail_count += 1
                if i == total - 1:  # 只记录最后一次
                    state_manager.add_operation_log(
                        f"上传文件: {uploaded_file.name}",
                        f"❌ 失败: {str(e)}",
                        False
                    )

            progress_bar.progress((i + 1) / total)

        if success_count > 0:
            st.success(f"✅ 成功上传 {success_count} 个文件" +
                       (f"，{fail_count} 个失败" if fail_count > 0 else ""))
            state_manager.add_operation_log(
                "批量上传完成",
                f"成功: {success_count}, 失败: {fail_count}",
                fail_count == 0
            )

        time.sleep(0.5)  # 减少等待时间
        st.rerun()

    except Exception as e:
        st.error(f"❌ 上传过程出错: {e}")
        state_manager.add_operation_log("批量上传", f"❌ 系统错误: {str(e)}", False)
    finally:
        progress_bar.empty()
        status_text.empty()

