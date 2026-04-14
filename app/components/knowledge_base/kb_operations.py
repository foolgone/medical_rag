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
            'pending_files': stats.get('pending_files', 0)
        }
    except Exception:
        return {
            'total_files': 0,
            'vectorized_files': 0,
            'pending_files': 0
        }


def _render_stats_card(stats: dict):
    """渲染统计卡片"""
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


def _render_operation_buttons(api_client: APIClient):
    """渲染操作按钮"""
    if st.button("⚡ 一键更新知识库", type="primary", use_container_width=True,
                 help="将所有未向量化的文件进行向量化处理"):
        handle_batch_vectorization(api_client)

    if st.button("🗑️ 清空知识库", use_container_width=True,
                 help="删除所有向量化数据（需谨慎操作）"):
        if st.warning("⚠️ 此操作将删除所有向量化数据，确定继续吗？"):
            if st.button("✅ 确认清空", type="primary", use_container_width=True):
                handle_clear_knowledge_base(api_client)


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
            st.success("✅ 知识库已清空")
            state_manager.add_operation_log(
                "清空知识库",
                "✅ 清空成功",
                True
            )
            time.sleep(1.5)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 清空失败: {e}")
        state_manager.add_operation_log("清空知识库", f"❌ 失败: {str(e)}", False)
