import sys

from toolforge import MCPServer


def main() -> None:
    # Set up a demo server
    server = MCPServer("demo")

    @server.tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @server.tool
    def greet(name: str) -> str:
        """Greet a user."""
        return f"Hello, {name}!"

    @server.tool
    def failing_tool() -> None:
        """Tool that intentionally fails."""
        raise RuntimeError("intentional test failure")

    # Ensure run() can execute when run directly
    print("Starting basic MCP server over stdio transport...", file=sys.stderr)
    server.run()


if __name__ == "__main__":
    main()
