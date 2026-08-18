import inspect
from typing import Any

from toolforge.errors import ToolExecutionError
from toolforge.registry import Tool


async def execute_tool(tool: Tool, arguments: dict[str, Any]) -> Any:
    """Execute a tool asynchronously with the provided arguments.

    If the underlying function is synchronous, it runs directly.
    If it is a coroutine, it is awaited.
    """
    from toolforge.validation import validate_tool_arguments

    # Validate and normalize arguments
    validated_args = validate_tool_arguments(tool, arguments)

    try:
        if inspect.iscoroutinefunction(tool.fn):
            return await tool.fn(**validated_args)
        else:
            return tool.fn(**validated_args)
    except Exception as e:
        raise ToolExecutionError(f"Error executing tool '{tool.name}': {e}") from e
