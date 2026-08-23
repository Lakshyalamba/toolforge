from collections.abc import Callable
from typing import Any, TypeVar

from mcptoolforge.registry import Tool

F = TypeVar("F", bound=Callable[..., Any])


class ToolDecorator:
    """Decorator to register functions as tools on a ToolRegistry.

    Supports both direct decorator style:
        @server.tool
        def my_tool(): ...

    And parameter style:
        @server.tool(name="custom_name", description="custom_desc")
        def my_tool(): ...
    """

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Check if used as @tool directly
        if len(args) == 1 and callable(args[0]) and not kwargs:
            func = args[0]
            tool = Tool(func)
            self._registry.register(tool)
            return func

        # Used as @tool(name=..., description=...)
        name: str | None = kwargs.get("name")
        description: str | None = kwargs.get("description")
        tags: list[str] | None = kwargs.get("tags")
        metadata: dict[str, Any] | None = kwargs.get("metadata")

        def decorator(func: F) -> F:
            tool = Tool(
                func,
                name=name,
                description=description,
                tags=tags,
                metadata=metadata,
            )
            self._registry.register(tool)
            return func

        return decorator
