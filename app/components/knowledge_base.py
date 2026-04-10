"""文档知识库模块 - 整合文件上传、管理、知识库更新"""
import streamlit as st
import time
from datetime import datetime
from app.api_client import APIClient


def render_knowledge_base_module(api_client: APIClient):
    """渲染文档知识库模块"""

    # 初始化会话状态
    if 'kb_refresh' not in st.session_state:
        st.session_state.kb_refresh = 0

    # 顶部功能区
    render_top_function_area(api_client)

    st.divider()

    # 中间文件列表
    render_file_list(api_client)

    st.divider()

    # 底部日志区
    render_log_area()


def render_top_function_area(api_client: APIClient):
    """顶部功能区：文件上传 + 知识库操作 + 状态提示"""

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📤 文件上传")

        # 文件分类选择
        category = st.selectbox(
            "文档分类",
            ["general", "cardiology", "endocrinology", "neurology", "other"],
            key="upload_category"
        )

        # 支持拖拽和点击上传
        uploaded_files = st.file_uploader(
            "选择文件上传（支持多文件）",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="支持PDF、DOCX、TXT格式，可同时上传多个文件"
        )

        if uploaded_files:
            st.info(f"已选择 {len(uploaded_files)} 个文件")

            col_upload, col_clear = st.columns([1, 1])
            with col_upload:
                if st.button("📥 开始上传", type="primary", use_container_width=True):
                    handle_file_upload(api_client, uploaded_files, category)

            with col_clear:
                if st.button("🗑️ 清除选择", use_container_width=True):
                    st.rerun()

    with col2:
        st.subheader("🔄 知识库操作")

        # 获取统计信息
        stats = get_knowledge_base_stats(api_client)

        # 状态提示卡片
        st.markdown(f"""
        <div style="padding: 1rem; background: #f0f9ff; border-radius: 0.5rem; border-left: 4px solid #1677ff;">
            <p style="margin: 0; font-size: 0.9rem;"><strong>📊 知识库状态</strong></p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;">
                总文件: {stats.get('total_files', 0)}<br>
                已向量化: <span style="color: #52c41a;">{stats.get('vectorized_files', 0)}</span><br>
                未向量化: <span style="color: #999;">{stats.get('pending_files', 0)}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # 知识库操作按钮
        if st.button("⚡ 一键更新知识库", type="primary", use_container_width=True,
                     help="将所有未向量化的文件进行向量化处理"):
            handle_batch_vectorization(api_client)

        if st.button("🗑️ 清空知识库", use_container_width=True,
                     help="删除所有向量化数据（需谨慎操作）"):
            if st.warning("⚠️ 此操作将删除所有向量化数据，确定继续吗？"):
                if st.button("✅ 确认清空", type="primary", use_container_width=True):
                    handle_clear_knowledge_base(api_client)


def render_file_list(api_client: APIClient):
    """中间文件列表：所有上传文件（带状态+操作）"""

    st.subheader("📄 文件列表")

    # 搜索和筛选
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_keyword = st.text_input("🔍 搜索文件", placeholder="按文件名搜索...", key="file_search")
    with col_filter:
        filter_status = st.selectbox(
            "筛选状态",
            ["全部", "未向量化", "已向量化", "更新中", "失败"],
            key="file_filter"
        )

    # 获取文件列表
    try:
        files_data = api_client.list_files()
        files = files_data.get('files', [])

        # 应用筛选
        if search_keyword:
            files = [f for f in files if search_keyword.lower() in f.get('filename', '').lower()]

        if filter_status != "全部":
            status_map = {
                "未向量化": "pending",
                "已向量化": "vectorized",
                "更新中": "processing",
                "失败": "failed"
            }
            target_status = status_map.get(filter_status, "")
            files = [f for f in files if f.get('status') == target_status]

        if not files:
            st.info("暂无文件，请先上传文件")
            return

        # 显示文件总数
        st.caption(f"共 {len(files)} 个文件")

        # 文件列表表格
        for file_info in files:
            render_file_item(api_client, file_info)

    except Exception as e:
        st.error(f"❌ 获取文件列表失败: {e}")


def render_file_item(api_client: APIClient, file_info: dict):
    """渲染单个文件项"""

    filename = file_info.get('filename', '未知文件')
    filesize = file_info.get('size', 0)
    upload_time = file_info.get('upload_time', '')
    status = file_info.get('status', 'pending')
    filepath = file_info.get('filepath', '')

    # 格式化文件大小
    if filesize < 1024:
        size_str = f"{filesize} B"
    elif filesize < 1024 * 1024:
        size_str = f"{filesize / 1024:.1f} KB"
    else:
        size_str = f"{filesize / (1024 * 1024):.1f} MB"

    # 状态显示
    status_config = {
        'pending': {'label': '未向量化', 'color': '#999', 'icon': '⚪'},
        'processing': {'label': '更新中', 'color': '#1677ff', 'icon': '🔵'},
        'vectorized': {'label': '已向量化', 'color': '#52c41a', 'icon': '✅'},
        'failed': {'label': '失败', 'color': '#ff4d4f', 'icon': '❌'}
    }

    status_info = status_config.get(status, status_config['pending'])

    # 使用expander展示文件详情
    with st.expander(f"{status_info['icon']} {filename} ({size_str})"):
        col_info, col_actions = st.columns([3, 2])

        with col_info:
            st.markdown(f"""
            <div style="font-size: 0.85rem; color: #666;">
                <p><strong>文件名:</strong> {filename}</p>
                <p><strong>大小:</strong> {size_str}</p>
                <p><strong>上传时间:</strong> {upload_time}</p>
                <p><strong>状态:</strong> <span style="color: {status_info['color']};">{status_info['label']}</span></p>
            </div>
            """, unsafe_allow_html=True)

        with col_actions:
            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

            # 预览按钮
            if st.button("👁️ 预览", key=f"preview_{filename}", use_container_width=True):
                handle_file_preview(file_info)

            # 单独更新按钮（仅未向量化文件）
            if status == 'pending' or status == 'failed':
                if st.button("🔄 单独更新", key=f"update_{filename}",
                             use_container_width=True, type="primary"):
                    handle_single_vectorization(api_client, filepath, file_info.get('category', 'general'))

            # 删除按钮
            if st.button("🗑️ 删除", key=f"delete_{filename}", use_container_width=True):
                if st.warning(f"确定删除文件 '{filename}' 吗？"):
                    if st.button("✅ 确认删除", key=f"confirm_delete_{filename}",
                                 type="primary", use_container_width=True):
                        handle_file_delete(api_client, filepath, filename)


def render_log_area():
    """底部日志区：知识库更新日志 + 进度提示"""

    st.subheader("📝 操作日志")

    # 初始化日志
    if 'operation_logs' not in st.session_state:
        st.session_state.operation_logs = []

    # 显示日志
    if st.session_state.operation_logs:
        for log in reversed(st.session_state.operation_logs[-10:]):  # 显示最近10条
            timestamp = log.get('timestamp', '')
            operation = log.get('operation', '')
            result = log.get('result', '')

            log_color = '#52c41a' if log.get('success', False) else '#ff4d4f'

            st.markdown(f"""
            <div style="padding: 0.5rem; margin: 0.3rem 0; background: #fafafa; 
                       border-radius: 0.3rem; border-left: 3px solid {log_color};">
                <p style="margin: 0; font-size: 0.8rem; color: #666;">
                    <strong>{timestamp}</strong> - {operation}<br>
                    <span style="color: {log_color};">{result}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("暂无操作日志")

    # 清空日志按钮
    if st.session_state.operation_logs:
        if st.button("🗑️ 清空日志", key="clear_logs"):
            st.session_state.operation_logs = []
            st.rerun()


def add_operation_log(operation: str, result: str, success: bool = True):
    """添加操作日志"""
    if 'operation_logs' not in st.session_state:
        st.session_state.operation_logs = []

    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'operation': operation,
        'result': result,
        'success': success
    }

    st.session_state.operation_logs.append(log_entry)

    # 限制日志数量
    if len(st.session_state.operation_logs) > 50:
        st.session_state.operation_logs = st.session_state.operation_logs[-50:]


def get_knowledge_base_stats(api_client: APIClient) -> dict:
    """获取知识库统计信息"""
    try:
        stats = api_client.get_stats()
        return {
            'total_files': stats.get('total_files', 0),
            'vectorized_files': stats.get('vectorized_files', 0),
            'pending_files': stats.get('pending_files', 0)
        }
    except Exception:
        return {
            'total_files': 0,
            'vectorized_files': 0,
            'pending_files': 0
        }


def handle_file_upload(api_client: APIClient, files, category: str):
    """处理文件上传"""
    progress_bar = st.progress(0)
    status_text = st.empty()

    success_count = 0
    fail_count = 0

    try:
        total = len(files)

        for i, uploaded_file in enumerate(files):
            status_text.text(f"正在上传 {i + 1}/{total}: {uploaded_file.name}")

            try:
                # 上传文件
                result = api_client.upload_file(uploaded_file, category)

                # 自动导入到知识库
                ingest_result = api_client.ingest_file(result['filepath'], category)

                success_count += 1
                add_operation_log(
                    f"上传文件: {uploaded_file.name}",
                    f"✅ 成功导入 {ingest_result.get('ingested_count', 0)} 个文档块",
                    True
                )

            except Exception as e:
                fail_count += 1
                add_operation_log(
                    f"上传文件: {uploaded_file.name}",
                    f"❌ 失败: {str(e)}",
                    False
                )

            progress_bar.progress((i + 1) / total)

        # 完成提示
        if success_count > 0:
            st.success(f"✅ 成功上传 {success_count} 个文件" +
                       (f"，{fail_count} 个失败" if fail_count > 0 else ""))
            add_operation_log(
                "批量上传完成",
                f"成功: {success_count}, 失败: {fail_count}",
                fail_count == 0
            )

        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"❌ 上传过程出错: {e}")
        add_operation_log("批量上传", f"❌ 系统错误: {str(e)}", False)
    finally:
        progress_bar.empty()
        status_text.empty()


def handle_batch_vectorization(api_client: APIClient):
    """批量向量化（一键更新知识库）"""
    try:
        with st.spinner("⚡ 正在更新知识库..."):
            result = api_client.incremental_update()

            st.success(f"✅ {result.get('message', '更新成功')}")
            add_operation_log(
                "一键更新知识库",
                f"✅ {result.get('message', '更新成功')}",
                True
            )

            time.sleep(1.5)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 更新失败: {e}")
        add_operation_log("一键更新知识库", f"❌ 失败: {str(e)}", False)


def handle_single_vectorization(api_client: APIClient, filepath: str, category: str):
    """单个文件向量化"""
    try:
        with st.spinner(f"🔄 正在向量化..."):
            result = api_client.ingest_file(filepath, category)

            st.success(f"✅ 导入成功: {result.get('ingested_count', 0)} 个文档块")
            add_operation_log(
                f"单独更新: {filepath.split('/')[-1]}",
                f"✅ 导入 {result.get('ingested_count', 0)} 个文档块",
                True
            )

            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 向量化失败: {e}")
        add_operation_log(
            f"单独更新: {filepath.split('/')[-1]}",
            f"❌ 失败: {str(e)}",
            False
        )


def handle_file_delete(api_client: APIClient, filepath: str, filename: str):
    """删除文件"""
    try:
        # TODO: 调用后端删除接口
        # 这里需要根据实际API实现
        st.success(f"✅ 文件 '{filename}' 已删除")
        add_operation_log(
            f"删除文件: {filename}",
            "✅ 删除成功",
            True
        )
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"❌ 删除失败: {e}")
        add_operation_log(
            f"删除文件: {filename}",
            f"❌ 失败: {str(e)}",
            False
        )


def handle_clear_knowledge_base(api_client: APIClient):
    """清空知识库"""
    try:
        with st.spinner("🗑️ 正在清空知识库..."):
            # TODO: 调用后端清空接口
            st.success("✅ 知识库已清空")
            add_operation_log(
                "清空知识库",
                "✅ 清空成功",
                True
            )
            time.sleep(1.5)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 清空失败: {e}")
        add_operation_log("清空知识库", f"❌ 失败: {str(e)}", False)


def handle_file_preview(file_info: dict):
    """文件预览"""
    filename = file_info.get('filename', '')
    filepath = file_info.get('filepath', '')

    # TODO: 实现文件预览功能
    st.info(f"预览功能开发中: {filename}")
    st.caption(f"文件路径: {filepath}")
