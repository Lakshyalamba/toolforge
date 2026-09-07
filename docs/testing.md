# Testing Guide

ToolForge includes a comprehensive, fast test suite covering protocol handling, registry operations, CLI commands, and the optional DSPy intelligence layer.

---

## Running Tests

### Standard Test Run
```bash
# Run all tests
pytest

# Verbose output with timing summary
pytest -v --durations=10

# Run a specific test module
pytest tests/test_dspy_mapper.py
pytest tests/test_intelligence_benchmark.py
```

---

## In-Process Server Testing with `MCPTestClient`

ToolForge provides `MCPTestClient` so you can test tools, resources, and prompts in-memory without spawning subprocesses or opening network ports:

```python
import pytest
from toolforge import MCPServer
from toolforge.testing import MCPTestClient


def test_add_tool():
    server = MCPServer("test-server")

    @server.tool
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

    client = MCPTestClient(server)

    # 1. Verify tool registration and schema
    tools = client.list_tools()
    assert any(t["name"] == "multiply" for t in tools)

    # 2. Invoke tool
    result = client.call_tool("multiply", {"a": 4, "b": 5})
    assert result == 20
```

---

## Testing the DSPy Intelligence Layer

When testing DSPy-related features, avoid making live LLM network requests in unit tests. Use mock modules or synthetic enrichers:

```python
from types import SimpleNamespace
from toolforge.intelligence.mapper import DSPyToolMapper
from toolforge.registry import Tool


def test_mapper_with_mock():
    def mock_enricher(tool_name: str, docstring: str, input_schema: dict):
        return SimpleNamespace(
            domain="database",
            category="query",
            primary_intent="Read database table rows",
            risk_level="safe",
            improved_description="Optimized query description",
            negative_examples=[],
            confidence=0.95,
        )

    mapper = DSPyToolMapper(enricher_module=mock_enricher)
    tool = Tool(fn=lambda: None, name="fetch_rows", description="Read rows")
    result = mapper.map_tool(tool)

    assert result.is_enriched is True
    assert result.semantics.domain == "database"
    assert result.semantics.risk_level.value == "safe"
```

---

## Benchmarking Tests

The quantitative evaluation framework includes dedicated tests under `tests/test_intelligence_benchmark.py`:
- Built-in 10-tool benchmark dataset integrity.
- Zero-token deterministic baseline verification.
- Side-by-side metric comparison calculations.
- Machine-readable JSON, CSV, and Markdown table serializations.
- CLI subcommand execution.
