"""工具函数"""
import json
from typing import Dict, List

def format_agent_event(event: Dict) -> str:
    """格式化Agent事件"""
    event_type = event.get("type", "unknown")

    if event_type == "tool_call":
        tools = event.get("tools", [])
        tool_names = ", ".join([t.get("name", "unknown") for t in tools])
        return f"🔧 调用工具: {tool_names}"
    elif event_type == "content":
        return event.get("content", "")
    elif event_type == "start":
        return "🔍 Agent正在思考..."
    elif event_type == "end":
        return ""
    elif event_type == "error":
        return f"❌ 错误: {event.get('error', '未知错误')}"

    return ""

def extract_tool_calls(events: List[Dict]) -> List[Dict]:
    """从事件流中提取工具调用"""
    tool_calls = []
    for event in events:
        if event.get("type") == "tool_call":
            tool_calls.extend(event.get("tools", []))
    return tool_calls
