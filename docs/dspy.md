# DSPy Integration Guide

ToolForge includes an optional intelligence layer powered by [DSPy](https://github.com/stanfordnlp/dspy) to augment deterministic MCP tools with LLM-powered semantic understanding, operational risk classification, prompt optimization, and agent tool execution.

---

## Architecture: Deterministic Core with Optional Intelligence

ToolForge keeps all protocol-level operations deterministic. JSON schema generation, transport handling, and local registration never require an LLM:

```text
MCP Server
  │
  ▼
Tool Discovery & Parameter Introspection
  │
  ▼
JSON Schema Processing
  │
  ├─────────────────────────────────────────────────┐
  │ (DSPy Disabled or Fallback)                    │ (DSPy Enabled)
  ▼                                                 ▼
StaticToolMapper (1:1 Passthrough)         DSPyToolMapper
                                                    │
                                            ┌───────┴───────┐
                                            ▼               ▼
                                       ToolEnricher   ToolDisambiguator
                                            │
                                            ▼
                                   ToolMappingResult (Semantics + Risk)
  ┌─────────────────────────────────────────────────┤
  ▼                                                 ▼
MCP Protocol Serving                     DSPyToolAdapter / ToolForgeAgent
```

---

## Core Signatures

DSPy programs in ToolForge are defined using declarative typed signatures:

1. **`ToolUnderstandingSignature`**:
   - Inputs: `tool_name`, `docstring`, `input_schema`
   - Outputs: `primary_intent`, `prerequisites`, `return_summary`
2. **`ToolClassificationSignature`**:
   - Inputs: `tool_name`, `docstring`, `input_schema`
   - Outputs: `domain` (service), `category` (operation), `risk_level` (`safe`, `idempotent`, `destructive`, `financial`, `unknown`), `rationale`
3. **`SemanticMappingSignature`**:
   - Inputs: `intent`, `candidate_tools`
   - Outputs: `selected_tool`, `confidence`, `arguments`

---

## Enabling DSPy

1. Install the DSPy extra:
   ```bash
   pip install "mcptoolforge[dspy]"
   ```
2. Enable in `pyproject.toml`:
   ```toml
   [tool.toolforge.dspy]
   enabled = true
   model = "openai/gpt-4o-mini"
   confidence_threshold = 0.6
   ```
3. Set your provider API key:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

---

## Offline Optimization (Few-Shot Compilation)

ToolForge can compile optimized mapping programs using DSPy teleprompters (such as `BootstrapFewShot`):

```bash
toolforge optimize --dataset dataset.json --output models/compiled_mapper.json
```

To load and use the compiled artifact in production:
```toml
[tool.toolforge.dspy]
enabled = true
compiled_program_path = "models/compiled_mapper.json"
```

---

## DSPy Agent & Tool Adapter

Expose ToolForge-generated MCP tools directly into DSPy ReAct/Predict agents without breaking existing signatures:

```python
import dspy
from toolforge import MCPServer
from toolforge.intelligence.tools import to_dspy_tools
from toolforge.intelligence.agent import ToolForgeAgent

server = MCPServer("agent-server")


@server.tool
def search_database(query: str) -> list[str]:
    """Search records in the database."""
    return [f"Result for {query}"]


# Convert ToolForge tools to DSPy-compatible tools
dspy_tools = to_dspy_tools(server.tools)

# Execute via ToolForgeAgent
agent = ToolForgeAgent(tools=server.tools)
result = agent.run("Find records matching 'user_account'")
print("Selected Tool:", result.selected_tool)
print("Execution Result:", result.output)
```

---

## Quantitative Benchmarking

Measure performance side-by-side using the reproducible benchmark suite:

```bash
toolforge benchmark --output-json results.json --output-csv results.csv
```

The benchmark measures:
1. **Tool Mapping Accuracy**
2. **Correct Service Identification**
3. **Correct Operation Identification**
4. **Invalid Mapping Rate**
5. **Fallback Rate**
6. **Average Wall-Clock Latency (ms)**
7. **Token & LLM API Usage**
8. **Failure Rate**
