from collections.abc import Callable
from typing import Any

from toolforge.decorators import ToolDecorator
from toolforge.prompts import Prompt, PromptDecorator, PromptRegistry
from toolforge.registry import Tool, ToolRegistry
from toolforge.resources import Resource, ResourceDecorator, ResourceRegistry


class MCPServer:
    """Core MCPServer abstraction class for registering and exposing tools."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.registry = ToolRegistry()
        self.tool = ToolDecorator(self.registry)
        self.resource_registry = ResourceRegistry()
        self.resource = ResourceDecorator(self.resource_registry)
        self.prompt_registry = PromptRegistry()
        self.prompt = PromptDecorator(self.prompt_registry)
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

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered by name."""
        return self.registry.contains(name)

    def list_tools(self) -> list[Tool]:
        """Return a list of all registered tools."""
        return self.registry.list()

    def as_dspy_tools(
        self,
        trace: Any | None = None,
        safety_gate: Any | None = None,
    ) -> list[Any]:
        """Convert all registered tools on this server into DSPy Tool instances."""
        from toolforge.intelligence.tools import to_dspy_tools

        return to_dspy_tools(self.tools, trace=trace, safety_gate=safety_gate)

    def get_resource(self, uri: str) -> Resource:
        """Retrieve a registered resource by URI."""
        return self.resource_registry.get(uri)

    def has_resource(self, uri: str) -> bool:
        """Check if a resource is registered by URI."""
        return self.resource_registry.contains(uri)

    def list_resources(self) -> list[Resource]:
        """Return a list of all registered resources."""
        return self.resource_registry.list()

    def get_prompt(self, name: str) -> Prompt:
        """Retrieve a registered prompt by name."""
        return self.prompt_registry.get(name)

    def has_prompt(self, name: str) -> bool:
        """Check if a prompt is registered by name."""
        return self.prompt_registry.contains(name)

    def list_prompts(self) -> list[Prompt]:
        """Return a list of all registered prompts."""
        return self.prompt_registry.list()
