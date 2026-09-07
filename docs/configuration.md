# Configuration Guide

ToolForge uses standard `pyproject.toml` tables for project and intelligence configuration.

---

## Minimal Configuration

```toml
[tool.toolforge]
name = "my-mcp-server"
entrypoint = "server.py"
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | string | required | Unique name identifying the MCP server. |
| `entrypoint` | string | `"server.py"` | Path to the Python file defining the `MCPServer` instance. |

---

## DSPy Intelligence Configuration

DSPy integration is completely optional and disabled by default. To enable semantic tool mapping, classification, and prompt optimization:

```toml
[tool.toolforge.dspy]
enabled = true                          # Default: false
model = "openai/gpt-4o-mini"             # LM provider and model identifier
temperature = 0.0                        # Generation temperature (0.0 to 2.0)
confidence_threshold = 0.6               # Minimum score before falling back (0.0 to 1.0)
compiled_program_path = "models/opt.json"# Optional path to saved compiled DSPy program

[tool.toolforge.dspy.optimization]
enabled = false                          # Enable prompt optimization
cache_dir = ".toolforge/intelligence"    # Directory for cached programs and demonstrations
max_bootstrapped_demos = 2               # Number of bootstrapped few-shot examples
max_labeled_demos = 2                    # Number of human-labeled demonstrations
```

### Field Reference

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `dspy.enabled` | boolean | `false` | When `true`, enables DSPy-powered semantic tool mapping. |
| `dspy.model` | string | `""` | Language model format supported by LiteLLM (e.g. `openai/gpt-4o-mini`, `anthropic/claude-3-5-sonnet`, `openrouter/...`). |
| `dspy.temperature` | float | `0.0` | Sampling temperature between `0.0` and `2.0`. |
| `dspy.confidence_threshold` | float | `0.6` | Minimum confidence score required to use semantic enrichment. Mappings scoring below fallback to `StaticToolMapper`. |
| `dspy.compiled_program_path` | string | `None` | Path to a compiled DSPy JSON state file produced by `toolforge optimize`. |
| `optimization.enabled` | boolean | `false` | Enables offline dataset-driven prompt optimization. |
| `optimization.cache_dir` | string | `".toolforge/intelligence"` | Directory where compiled artifacts and datasets are cached. |
| `optimization.max_bootstrapped_demos` | integer | `2` | Maximum few-shot demonstrations to bootstrap from dataset. |
| `optimization.max_labeled_demos` | integer | `2` | Maximum labeled examples to retain in prompt context. |

---

## Secret Management

> [!IMPORTANT]
> Never put API keys, bearer tokens, or sensitive credentials inside `pyproject.toml`.

ToolForge resolves credentials from standard environment variables:
- **OpenAI**: `export OPENAI_API_KEY="sk-..."`
- **Anthropic**: `export ANTHROPIC_API_KEY="sk-ant-..."`
- **OpenRouter**: `export OPENROUTER_API_KEY="sk-or-..."`
- **Google / Gemini**: `export GEMINI_API_KEY="..."`

---

## Validation & Fallbacks

- If `dspy.enabled = true` but `dspy` is not installed, ToolForge raises `DSPyNotInstalledError` when DSPy is explicitly invoked, but continues operating deterministic features normally.
- If `dspy.model` is missing or temperature is outside `[0.0, 2.0]`, a `ConfigurationError` is raised on startup.
- If DSPy inference times out, raises an unhandled exception, or returns confidence below `confidence_threshold`, ToolForge automatically falls back to `StaticToolMapper`.
