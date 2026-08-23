# Getting Started

MCPToolForge is a developer-friendly Python framework for creating Model Context Protocol (MCP) servers with minimal boilerplate.

## Installation

Install the package via pip:
```bash
pip install mcptoolforge
```

## Quick Start Example

Here is how you can define an MCP server with a custom tool:

```python
from toolforge import MCPServer

# Create server instance
server = MCPServer("my-server")


# Register a custom tool
@server.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


if __name__ == "__main__":
    server.run()
```

## Run Locally

You can run your server script directly:
```bash
python my_server.py
```

Or run via the built-in CLI:
```bash
toolforge run my_server.py
```
