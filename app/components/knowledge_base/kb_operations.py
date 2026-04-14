"""知识库操作组件"""
import streamlit as st
import time
from app.api_client import APIClient
from app.state_manager import state_manager


def render_kb_operations(api_client: APIClient):
    """渲染知识库操作区域"""
    st.subheader("🔄 知识库操作")

    stats = _get_knowledge_base_stats(api_client)
    _render_stats_card(stats)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    _render_operation_buttons(api_client)


def _get_knowledge_base_stats(api_client: APIClient) -> dict:
    """获取知识库统计信息"""
    try:
        stats = api_client.get_stats()
        return {
            'total_files': stats.get('total_files', 0),
            'vectorized_files': stats.get('vectorized_files', 0),
            'pending_files': stats.get('pending_files', 0),
            'total_versions': stats.get('total_versions', 0),
            'active_versions': stats.get('active_versions', 0),
            'failed_jobs': stats.get('failed_jobs', 0),
            'latest_version_time': stats.get('latest_version_time'),
        }
    except Exception:
        return {
            'total_files': 0,
            'vectorized_files': 0,
            'pending_files': 0,
            'total_versions': 0,
            'active_versions': 0,
            'failed_jobs': 0,
            'latest_version_time': None,
        }


def _render_stats_card(stats: dict):
    """渲染统计卡片"""
    st.markdown(f"""
    <div style="padding: 1rem; background: #f0f9ff; border-radius: 0.5rem; border-left: 4px solid #1677ff;">
        <p style="margin: 0; font-size: 0.9rem;"><strong>📊 知识库状态</strong></p>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;">
            总文件: {stats.get('total_files', 0)}<br>
            已向量化: <span style="color: #52c41a;">{stats.get('vectorized_files', 0)}</span><br>
            未向量化: <span style="color: #999;">{stats.get('pending_files', 0)}</span><br>
            总版本数: {stats.get('total_versions', 0)}<br>
            当前生效版本: {stats.get('active_versions', 0)}<br>
            失败任务: <span style="color: #ff4d4f;">{stats.get('failed_jobs', 0)}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    latest_version_time = stats.get("latest_version_time")
    if latest_version_time:
        st.caption(f"最近一次版本更新时间：{latest_version_time}")


def _render_operation_buttons(api_client: APIClient):
    """渲染操作按钮"""
    if st.button("⚡ 一键更新知识库", type="primary", use_container_width=True,
                 help="将所有待处理文件更新入库，并生成最新可用版本"):
        handle_batch_vectorization(api_client)

    if st.button("🗑️ 清空知识库", use_container_width=True,
                 help="删除所有向量化数据（需谨慎操作）"):
        st.session_state["confirm_clear_kb"] = True

    if st.session_state.get("confirm_clear_kb"):
        st.warning("⚠️ 此操作将删除所有知识库版本记录和向量数据，确定继续吗？")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("✅ 确认清空", type="primary", use_container_width=True):
                handle_clear_knowledge_base(api_client)
                st.session_state["confirm_clear_kb"] = False
        with cancel_col:
            if st.button("取消", use_container_width=True):
                st.session_state["confirm_clear_kb"] = False


def handle_batch_vectorization(api_client: APIClient):
    """批量向量化"""
    try:
        with st.spinner("⚡ 正在更新知识库..."):
            result = api_client.incremental_update()
            success = result.get('success', False)
            message = result.get('message', '更新成功')

            if success:
                st.success(f"✅ {message}")
                state_manager.add_operation_log(
                    "一键更新知识库",
                    f"✅ {message}",
                    True
                )

                time.sleep(1.5)
                st.rerun()
                return

            st.error(f"❌ {message}")
            state_manager.add_operation_log(
                "一键更新知识库",
                f"❌ {message}",
                False
            )

    except Exception as e:
        st.error(f"❌ 更新失败: {e}")
        state_manager.add_operation_log("一键更新知识库", f"❌ 失败: {str(e)}", False)


def handle_clear_knowledge_base(api_client: APIClient):
    """清空知识库"""
    try:
        with st.spinner("🗑️ 正在清空知识库..."):
            result = api_client.delete_by_rule()
            if not result.get("success", False):
                raise RuntimeError(result.get("message", "清空失败"))

            st.success(f"✅ {result.get('message', '知识库已清空')}")
            state_manager.add_operation_log(
                "清空知识库",
                f"✅ {result.get('message', '清空成功')}",
                True
            )
            time.sleep(1.5)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 清空失败: {e}")
        state_manager.add_operation_log("清空知识库", f"❌ 失败: {str(e)}", False)
