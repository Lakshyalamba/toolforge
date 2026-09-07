# MCPToolForge

A developer-friendly Python framework for creating, testing, and exposing Model Context Protocol (MCP) servers with minimal boilerplate, featuring an optional DSPy-powered semantic intelligence layer.

---

## What Problem MCPToolForge Solves

The Model Context Protocol (MCP) standardizes how LLM applications discover and invoke external tools, resources, and prompt templates. However, building MCP servers directly with raw protocol primitives often requires extensive boilerplate for JSON-RPC message handling, manual parameter schema drafting, and transport management.

MCPToolForge provides:
1. **Zero-Boilerplate Server Definition**: Define tools with standard Python functions, type annotations, and docstrings. ToolForge automatically derives standard JSON Schemas and handles STDIO/SSE transports.
2. **In-Process Testing**: Validate tools, resources, and prompts locally with `MCPTestClient` without launching subprocesses.
3. **Optional DSPy Semantic Intelligence**: Augment deterministic tool registries with semantic understanding, operational risk classification (`safe`, `idempotent`, `destructive`, `financial`), prompt-optimized descriptions, few-shot compilation, and intelligent tool selection.

---

## Installation

Install core MCPToolForge:
```bash
pip install mcptoolforge
```

To enable the optional DSPy intelligence and optimization layer:
```bash
pip install "mcptoolforge[dspy]"
```

---

## Quick Start

Create a minimal MCP server in `server.py`:

```python
from toolforge import MCPServer

server = MCPServer("demo-server")


@server.tool
def calculate_area(length: float, width: float) -> float:
    """Calculate the area of a rectangle.

    Args:
        length: Length of the rectangle.
        width: Width of the rectangle.
    """
    return length * width


if __name__ == "__main__":
    server.run()
```

Run the server directly or using the CLI:
```bash
toolforge run server.py
```

---

## Command-Line Interface (CLI)

ToolForge includes a built-in CLI for server management, inspection, and intelligence:

| Command | Description |
| :--- | :--- |
| `toolforge init [DIR]` | Scaffold a new ToolForge project. |
| `toolforge run [FILE]` | Start the MCP server transport loop. |
| `toolforge list` | List all registered tools, resources, and prompts. |
| `toolforge inspect [NAME]` | Inspect schemas and metadata for a specific tool. |
| `toolforge map [NAME]` | Inspect semantic understanding and classifications. |
| `toolforge evaluate --dataset FILE` | Evaluate mapping accuracy against a dataset. |
| `toolforge optimize --dataset FILE` | Compile optimized DSPy few-shot demonstrations. |
| `toolforge benchmark` | Run quantitative side-by-side benchmark (Baseline vs DSPy). |

---

## Optional DSPy Intelligence Layer

ToolForge preserves a deterministic baseline while offering DSPy as an optional intelligence layer. When enabled, ToolForge enriches registered tools with:
- **Semantic Domain & Category**: Functional grouping (e.g. `database`, `filesystem`) and operational category (e.g. `query`, `mutation`).
- **Operational Risk Assessment**: Categorization into `safe`, `idempotent`, `destructive`, or `financial`.
- **Improved Docstrings**: Rewritten descriptions engineered for downstream LLM tool selection.
- **Ambiguity Resolution & Agent Selection**: Semantic selection of tools for high-level user queries.
- **Graceful Fallback**: If DSPy is disabled or fails, ToolForge falls back to deterministic static mapping.

Enable DSPy in `pyproject.toml`:
```toml
[tool.toolforge.dspy]
enabled = true
model = "openai/gpt-4o-mini"
confidence_threshold = 0.6
```

---

## Documentation

- [Getting Started](docs/getting-started.md)
- [Architecture & Pipelines](docs/architecture.md)
- [Configuration Reference](docs/configuration.md)
- [DSPy Integration Guide](docs/dspy.md)
- [Testing Guide](docs/testing.md)
- [Contributing Guide](CONTRIBUTING.md)

---

## Contributing & Development

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup, testing, and PR submission guidelines.

```bash
# Setup development environment
git clone https://github.com/Lakshyalamba/toolforge.git
cd toolforge
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,dspy]"

# Run tests
pytest

# Code formatting & linting
ruff check .
ruff format --check .
```

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
