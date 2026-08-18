from toolforge.decorators import ToolDecorator
from toolforge.registry import Tool, ToolRegistry


class MCPServer:
    """Core MCPServer abstraction class for registering and exposing tools."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.registry = ToolRegistry()
        self.tool = ToolDecorator(self.registry)

    def run(self) -> None:
        """Run the MCP server over STDIO transport."""
        import anyio

        from toolforge.mcp.server import MCPServerRunner

        runner = MCPServerRunner(self.name, self.registry)
        anyio.run(runner.run_async)

    @property
    def tools(self) -> list[Tool]:
        """Return a list of all registered tools on this server."""
        return self.registry.list()

    def get_tool(self, name: str) -> Tool:
        """Retrieve a registered tool by name."""
        return self.registry.get(name)
