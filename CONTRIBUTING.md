# Contributing to MCPToolForge

Thank you for contributing to MCPToolForge! This guide explains how to set up your environment, run tests, adhere to coding standards, add new mappers or generators, and submit Pull Requests.

---

## Development Setup

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/toolforge.git
cd toolforge
```

### 2. Virtual Environment
Create and activate a virtual environment (Python 3.11+ required):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Editable Dependencies
Install all core, development, and optional DSPy dependencies:
```bash
pip install -e ".[dev,dspy]"
```

---

## Running Tests & Quality Checks

### Run Unit & Integration Tests
```bash
# Run complete test suite
pytest

# Run a specific test module
pytest tests/test_dspy_mapper.py

# Run with verbose output
pytest -v
```

### Code Formatting & Linting
ToolForge enforces strict style using [Ruff](https://astral.sh/ruff):
```bash
# Lint checks
ruff check .

# Apply safe automatic fixes
ruff check --fix .

# Code formatting checks
ruff format --check .

# Auto-format files
ruff format .
```

---

## Extending ToolForge

### How to Add a New Mapper
All mappers implement the `ToolMapper` abstract base class defined in `toolforge.intelligence.mapper.base`:

```python
from toolforge.intelligence.mapper.base import ToolMapper
from toolforge.intelligence.models import ToolMappingResult
from toolforge.registry import Tool


class CustomToolMapper(ToolMapper):
    """Custom mapper mapping tools to domain-specific metadata."""

    def map_tool(self, tool: Tool) -> ToolMappingResult:
        # Implement mapping logic: extract semantics or transform metadata
        return ToolMappingResult(
            name=tool.name,
            original_description=tool.description,
            effective_description=tool.description,
            input_schema=tool.input_schema,
            semantics=None,
            is_enriched=False,
            confidence=1.0,
            mapping_source="custom",
        )

    def map_tools(self, tools: list[Tool]) -> list[ToolMappingResult]:
        return [self.map_tool(t) for t in tools]

    def resolve_ambiguity(
        self, intent: str, candidate_tools: list[Tool]
    ) -> tuple[Tool, float, str]:
        # Disambiguate when multiple tools could handle an intent
        return candidate_tools[0], 1.0, "Selected by custom rule."
```

Register your mapper in `toolforge.intelligence.mapper` and add unit tests under `tests/`.

### How to Add a New Generator
Generators transform registered `Tool` objects or `ToolMappingResult` instances into external formats (e.g. client SDK stubs, OpenAPI schemas, or agent definitions):

1. Define a generator function or class in `toolforge.schema` or a new module under `toolforge.generators`.
2. Accept a `Tool` or list of `Tool` / `ToolMappingResult` objects.
3. Access `tool.name`, `tool.description`, `tool.input_schema`, and `tool.semantics` (if enriched).
4. Return the generated schema dictionary or formatted code string.
5. Provide tests verifying generation from standard tool definitions and edge-case parameter signatures.

---

## Submitting a Pull Request (PR)

1. **Create a Branch**:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. **Follow Conventional Commits**:
   - `feat: add support for streaming tools`
   - `fix: resolve parameter coercion error for booleans`
   - `docs: update configuration guide`
   - `test: add benchmark runner edge-case tests`
3. **Verify Checks**:
   Ensure `pytest`, `ruff check .`, and `ruff format --check .` pass locally with 0 errors.
4. **Push & Open PR**:
   Push your branch and open a PR against `main`. Provide a clear description of changes, motivation, and test evidence.
5. **No Secrets**: Never commit real API keys or private tokens.

---

## Need Help?
Open an issue on [GitHub Issues](https://github.com/Lakshyalamba/toolforge/issues) to ask questions or propose design ideas before submitting large PRs.
