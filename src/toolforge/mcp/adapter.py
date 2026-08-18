import logging
from typing import Any

import mcp.types as t
from mcp.server.context import ServerRequestContext
from mcp.shared.exceptions import MCPError

from toolforge.errors import ToolExecutionError, ToolNotFoundError
from toolforge.execution import execute_tool
from toolforge.registry import ToolRegistry

logger = logging.getLogger("toolforge.mcp")


class MCPAdapter:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def handle_list_tools(
        self,
        ctx: ServerRequestContext[Any],
        params: t.PaginatedRequestParams,
    ) -> t.ListToolsResult:
        mcp_tools = []
        for tf_tool in self.registry.list():
            mcp_tool = t.Tool(
                name=tf_tool.name,
                description=tf_tool.description,
                input_schema=tf_tool.input_schema,
            )
            mcp_tools.append(mcp_tool)
        return t.ListToolsResult(tools=mcp_tools)

    async def handle_call_tool(
        self,
        ctx: ServerRequestContext[Any],
        params: t.CallToolRequestParams,
    ) -> t.CallToolResult:
        try:
            try:
                tf_tool = self.registry.get(params.name)
            except ToolNotFoundError as e:
                raise MCPError(code=-32601, message=str(e)) from e

            arguments = params.arguments or {}

            try:
                result = await execute_tool(tf_tool, arguments)
            except ToolExecutionError as e:
                logger.error(f"Execution failed for tool '{params.name}': {e}", exc_info=True)
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=str(e))],
                    is_error=True,
                )

            if isinstance(result, dict):
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=str(result))],
                    structured_content=result,
                    is_error=False,
                )
            else:
                text_value = result if isinstance(result, str) else str(result)
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=text_value)],
                    is_error=False,
                )

        except MCPError:
            raise
        except Exception as e:
            logger.critical(f"Internal ToolForge error in call_tool: {e}", exc_info=True)
            raise MCPError(code=-32603, message=f"Internal ToolForge error: {e}") from e
