from typing import Any

from mcptoolforge.registry import Tool


class MiddlewareContext:
    """Structured context passed to MCPToolForge middleware containing tool execution details."""

    def __init__(self, tool_name: str, tool: Tool, arguments: dict[str, Any], server: Any) -> None:
        self.tool_name = tool_name
        self.tool = tool
        self.arguments = arguments
        self.server = server
        self.error: Exception | None = None
        self.duration: float | None = None
