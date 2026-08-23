import sys

from toolforge import MCPServer

server = MCPServer("resource-demo")


@server.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@server.resource(
    "config://app",
    description="Application configuration",
    mime_type="application/json",
)
def app_config():
    return {
        "name": "ToolForge",
        "environment": "development",
    }


if __name__ == "__main__":
    print("Starting resources demo server...", file=sys.stderr)
    server.run()
