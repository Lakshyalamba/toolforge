import inspect
from typing import Any

from toolforge.errors import ToolExecutionError
from toolforge.registry import Tool


async def execute_tool(tool: Tool, arguments: dict[str, Any]) -> Any:
    """Execute a tool asynchronously with the provided arguments.
    
    If the underlying function is synchronous, it runs directly.
    If it is a coroutine, it is awaited.
    """
    for param_name, param in tool.parameters.items():
        if param.required and param_name not in arguments:
            raise ToolExecutionError(
                f"Missing required argument: '{param_name}' for tool '{tool.name}'."
            )

    try:
        if inspect.iscoroutinefunction(tool.fn):
            return await tool.fn(**arguments)
        else:
            return tool.fn(**arguments)
    except Exception as e:
        raise ToolExecutionError(f"Error executing tool '{tool.name}': {e}") from e
