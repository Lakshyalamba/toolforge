# MCPToolForge

A developer-friendly Python framework for creating and exposing Model Context Protocol (MCP) servers with minimal boilerplate.

---

## What MCPToolForge Does
MCPToolForge wraps the low-level JSON-RPC protocol details and STDIO transport mechanisms of the Model Context Protocol, offering simple Python decorators to register Tools, Resources, and Prompts.

## Key Features
- **Decorator API**: Register `@server.tool`, `@server.resource`, and `@server.prompt` handlers easily.
- **Automatic Schema Generation**: Introspects python function signatures and type hints to generate correct JSON Schema parameter descriptions.
- **Middleware & Hooks**: Built-in support for timing, logging, and startup/shutdown lifecycle hooks.
- **Local Testing Client**: Test your tools, resources, and prompts completely in-process using `MCPTestClient`.
- **Built-in CLI**: Clean command-line utility to initialize templates, run servers, list registries, and inspect configurations.

---

## Installation
```bash
pip install mcptoolforge
```

---

## Quick Start Example

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

## Development Setup
Get up and running for local development:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Testing
Run the pytest suite to verify all checks pass locally:
```bash
pytest
```

---

## Contribution
To get started with contributing, fork/clone the repo, create a branch, and open a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License
Distributed under the MIT License. See [LICENSE](LICENSE) for details.
