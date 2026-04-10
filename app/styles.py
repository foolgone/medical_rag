"""样式管理器 - 统一管理CSS样式"""


class StyleManager:
    """样式管理器"""
    
    @staticmethod
    def get_global_styles() -> str:
        """获取全局样式"""
        return """
        <style>
            /* 全局样式 */
            .main-header {
                font-size: 2.2rem;
                font-weight: 600;
                background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
                margin-bottom: 1.5rem;
            }
            
            /* 侧边栏样式 */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #fafafa 0%, #f5f5f5 100%);
            }
            
            /* 按钮悬停效果 */
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                transition: all 0.3s ease;
            }
            
            /* 卡片阴影 */
            div[data-testid="stExpander"] {
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                border-radius: 0.5rem;
            }
            
            /* 加载动画 */
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            /* 消息气泡 */
            .message-user {
                display: flex;
                justify-content: flex-end;
                margin: 0.5rem 0;
            }
            
            .message-assistant {
                display: flex;
                justify-content: flex-start;
                margin: 0.5rem 0;
            }
        </style>
        """
    
    @staticmethod
    def get_user_message_style() -> str:
        """用户消息样式"""
        return """
        display: flex; 
        justify-content: flex-end; 
        margin: 0.5rem 0;
        """
    
    @staticmethod
    def get_user_bubble_style() -> str:
        """用户消息气泡样式"""
        return """
        max-width: 70%; 
        padding: 1rem; 
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
        border-radius: 1rem 1rem 0.2rem 1rem; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        """
    
    @staticmethod
    def get_assistant_bubble_style() -> str:
        """AI助手消息气泡样式"""
        return """
        max-width: 70%; 
        padding: 1rem; 
        background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%); 
        border-radius: 1rem 1rem 1rem 0.2rem; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        """
    
    @staticmethod
    def get_tool_call_box_style() -> str:
        """工具调用信息框样式"""
        return """
        margin-top: 0.5rem; 
        padding: 0.5rem; 
        background: #e8f5e9; 
        border-radius: 0.5rem; 
        border-left: 3px solid #4caf50;
        """
    
    @staticmethod
    def get_reference_box_style() -> str:
        """引用信息框样式"""
        return """
        margin-top: 0.5rem; 
        padding: 0.5rem; 
        background: #fff3e0; 
        border-radius: 0.5rem; 
        border-left: 3px solid #ff9800;
        """
    
    @staticmethod
    def get_loading_status_style(color: str = "#1976d2") -> str:
        """加载状态样式"""
        return f"""
        <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; 
                   background: #e3f2fd; border-radius: 0.5rem;">
            <div style="width: 16px; height: 16px; border: 2px solid {color}; 
                       border-top-color: transparent; border-radius: 50%; 
                       animation: spin 1s linear infinite;"></div>
            <span style="font-size: 0.9rem; color: {color};">加载中...</span>
        </div>
        """
    
    @staticmethod
    def get_info_card_style() -> str:
        """信息卡片样式"""
        return """
        padding: 1rem; 
        background: #f0f9ff; 
        border-radius: 0.5rem; 
        border-left: 4px solid #1677ff;
        """
    
    @staticmethod
    def get_warning_box_style() -> str:
        """警告框样式"""
        return """
        text-align: center; 
        padding: 0.5rem; 
        margin-top: 0.5rem; 
        background: #fff9e6; 
        border-radius: 0.3rem; 
        border: 1px solid #ffe58f;
        """
    
    @staticmethod
    def get_sidebar_stats_style() -> str:
        """侧边栏统计样式"""
        return """
        padding: 0.8rem; 
        background: white; 
        border-radius: 0.5rem; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        """
    
    @staticmethod
    def get_file_item_style(status_color: str) -> str:
        """文件项样式"""
        return f"""
        padding: 0.5rem; 
        margin: 0.3rem 0; 
        background: #fafafa; 
        border-radius: 0.3rem; 
        border-left: 3px solid {status_color};
        """


# 全局样式管理器实例
style_manager = StyleManager()
