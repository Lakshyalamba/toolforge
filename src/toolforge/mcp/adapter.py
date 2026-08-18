import logging
from typing import Any

import mcp.types as t
from mcp.server.context import ServerRequestContext
from mcp.shared.exceptions import MCPError

from toolforge.errors import (
    ConfigurationError,
    MiddlewareError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from toolforge.execution import execute_tool
from toolforge.registry import ToolRegistry

logger = logging.getLogger("toolforge.mcp")


class MCPAdapter:
    """Adapts ToolForge ToolRegistry and tools to the MCP protocol server."""

    def __init__(self, registry: ToolRegistry, server: Any = None) -> None:
        self.registry = registry
        self.server = server

    async def handle_list_tools(
        self,
        ctx: ServerRequestContext[Any],
        params: t.PaginatedRequestParams | None,
    ) -> t.ListToolsResult:
        """Map registered ToolForge tools to MCP Tool representations."""
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
        """Execute the requested tool and translate results/errors to MCP format."""
        try:
            # 1. Locate the tool
            try:
                tf_tool = self.registry.get(params.name)
            except ToolNotFoundError as e:
                raise MCPError(code=-32601, message=str(e)) from e

            # 2. Extract arguments
            arguments = params.arguments or {}

            # 3. Execute the tool (wrapping with middlewares if configured)
            try:
                if self.server and self.server.middlewares:
                    import inspect
                    import time

                    from toolforge.middleware.context import MiddlewareContext
                    from toolforge.middleware.manager import build_chain, is_async_callable

                    context = MiddlewareContext(
                        tool_name=tf_tool.name,
                        tool=tf_tool,
                        arguments=arguments,
                        server=self.server,
                    )

                    called_next = False

                    if inspect.iscoroutinefunction(tf_tool.fn):

                        async def final_call() -> Any:
                            nonlocal called_next
                            called_next = True
                            from toolforge.validation import validate_tool_arguments

                            validated_args = validate_tool_arguments(tf_tool, context.arguments)

                            try:
                                return await tf_tool.fn(**validated_args)
                            except Exception as inner_e:
                                if not isinstance(
                                    inner_e, (ToolValidationError, ToolExecutionError)
                                ):
                                    raise ToolExecutionError(
                                        f"Error executing tool '{tf_tool.name}': {inner_e}"
                                    ) from inner_e
                                raise

                    else:

                        def final_call() -> Any:
                            nonlocal called_next
                            called_next = True
                            from toolforge.validation import validate_tool_arguments

                            validated_args = validate_tool_arguments(tf_tool, context.arguments)

                            try:
                                return tf_tool.fn(**validated_args)
                            except Exception as inner_e:
                                if not isinstance(
                                    inner_e, (ToolValidationError, ToolExecutionError)
                                ):
                                    raise ToolExecutionError(
                                        f"Error executing tool '{tf_tool.name}': {inner_e}"
                                    ) from inner_e
                                raise

                    start_time = time.perf_counter()
                    chain_callable = build_chain(self.server.middlewares, context, final_call)

                    try:
                        if inspect.iscoroutinefunction(chain_callable) or is_async_callable(
                            chain_callable
                        ):
                            result = await chain_callable()
                        else:
                            result = chain_callable()
                        context.duration = time.perf_counter() - start_time
                    except Exception as e:
                        context.duration = time.perf_counter() - start_time
                        context.error = e
                        if called_next and isinstance(e, (ToolValidationError, ToolExecutionError)):
                            raise
                        else:
                            raise MiddlewareError(f"Middleware failed during execution: {e}") from e
                else:
                    result = await execute_tool(tf_tool, arguments)

            except ToolValidationError as e:
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=str(e))],
                    is_error=True,
                )
            except (ToolExecutionError, MiddlewareError, ConfigurationError) as e:
                logger.error(f"Execution failed for tool '{params.name}': {e}", exc_info=True)
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=str(e))],
                    is_error=True,
                )

            # 4. Map return result to CallToolResult
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
