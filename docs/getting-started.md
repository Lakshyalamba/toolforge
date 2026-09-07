# Getting Started

MCPToolForge is a developer-friendly Python framework for creating Model Context Protocol (MCP) servers with minimal boilerplate.

---

## Installation

Install core ToolForge:
```bash
pip install mcptoolforge
```

Or install with optional DSPy intelligence:
```bash
pip install "mcptoolforge[dspy]"
```

---

## Quick Start Example

Define an MCP server with a custom tool in `server.py`:

```python
from toolforge import MCPServer

server = MCPServer("my-server")


@server.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


if __name__ == "__main__":
    server.run()
```

---

## Running the Server

Run your server script directly:
```bash
python server.py
```

Or run via the built-in CLI:
```bash
toolforge run server.py
```

---

## Next Steps

- [Configuration Reference](configuration.md)
- [DSPy Intelligence Layer](dspy.md)
- [Architecture & Pipelines](architecture.md)
- [Testing Guide](testing.md)
- [Contributing](contributing.md)
