from collections.abc import Callable

from toolforge.decorators import ToolDecorator
from toolforge.registry import Tool, ToolRegistry


class MCPServer:
    """Core MCPServer abstraction class for registering and exposing tools."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.registry = ToolRegistry()
        self.tool = ToolDecorator(self.registry)
        self.middlewares: list[Callable] = []
        self.startup_hooks: list[Callable] = []
        self.shutdown_hooks: list[Callable] = []

    def middleware(self, fn: Callable) -> Callable:
        """Decorator to register a middleware function."""
        self.middlewares.append(fn)
        return fn

    def add_middleware(self, fn: Callable) -> None:
        """Programmatically register a middleware function."""
        self.middlewares.append(fn)

    def on_startup(self, fn: Callable) -> Callable:
        """Decorator to register a startup lifecycle hook."""
        self.startup_hooks.append(fn)
        return fn

    def on_shutdown(self, fn: Callable) -> Callable:
        """Decorator to register a shutdown lifecycle hook."""
        self.shutdown_hooks.append(fn)
        return fn

    def run(self) -> None:
        """Run the MCP server over STDIO transport."""
        import anyio

        from toolforge.mcp.server import MCPServerRunner

        runner = MCPServerRunner(self.name, self.registry, server=self)
        anyio.run(runner.run_async)

    @property
    def tools(self) -> list[Tool]:
        """Return a list of all registered tools on this server."""
        return self.registry.list()

    def get_tool(self, name: str) -> Tool:
        """Retrieve a registered tool by name."""
        return self.registry.get(name)
