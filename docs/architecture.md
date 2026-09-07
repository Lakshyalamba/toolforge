# Architecture & Pipeline

MCPToolForge bridges Python functions with the Model Context Protocol (MCP), providing a clean developer API for server definition and an optional semantic intelligence layer powered by DSPy.

---

## End-to-End Pipeline

```text
MCP Server (@server.tool)
       │
       ▼
1. Tool Discovery & Parameter Introspection (inspect, type_hints)
       │
       ▼
2. Schema Processing (toolforge.schema -> JSON Schema)
       │
       ▼
3. Tool Mapping Layer (ToolMapper interface)
       ├── Deterministic (StaticToolMapper) -> 1:1 Passthrough (0 tokens, ~0.01ms)
       └── AI-Enhanced  (DSPyToolMapper)   -> Semantic enrichment, risk level, optimized docstrings
       │
       ▼
4. Generation & Consumer Layer
       ├── MCP JSON-RPC Server Transport (STDIO / SSE to Claude, Cursor, etc.)
       └── DSPy Tool Adapter (to_dspy_tools -> ToolForgeAgent / ReAct)
```

---

## Core Components

### 1. `MCPServer` & Registry Layer
- **`MCPServer`**: Main application lifecycle coordinator. Manages tools, resources, prompts, and server transport loops.
- **Registries**: Internal maps (`tools`, `resources`, `prompts`) with fast indexed lookups and validation.
- **Middleware Pipeline**: Onion-style wrappers for request timing, error handling, structured logging, and lifecycle events (`@server.on_startup`, `@server.on_shutdown`).

### 2. Schema Generation (`toolforge.schema`)
Introspects Python callables and type annotations to generate valid JSON Schema draft-07 parameter schemas without requiring Pydantic or manual schema definitions.

### 3. Intelligence Layer (`toolforge.intelligence`)
- **`ToolMapper`**: Base interface with `map_tool()`, `map_tools()`, and `resolve_ambiguity()`.
- **`StaticToolMapper`**: Zero-overhead deterministic baseline.
- **`DSPyToolMapper`**: Enriches tools with domains, operational categories, risk levels (`safe`, `idempotent`, `destructive`, `financial`), and improved descriptions.
- **`MapperOptimizer`**: Offline compilation engine that tunes prompts and selects few-shot demonstrations using DSPy teleprompters.
- **`ToolForgeAgent` & `DSPyToolAdapter`**: Adapter layer exposing ToolForge tools directly into DSPy agent workflows.
- **`BenchmarkRunner`**: Evaluates baseline vs DSPy side-by-side across accuracy, latency, fallback rate, and token usage.

---

## Extension Points

ToolForge is designed for easy extensibility:

1. **Custom Mappers**: Subclass `ToolMapper` to implement domain-specific tool understanding or integrate alternate AI frameworks.
2. **Custom Generators**: Build generators in `toolforge.generators` to translate registered tools or enriched `ToolMappingResult` objects into OpenAPI specifications, TypeScript client SDKs, or CLI bindings.
3. **Custom Middlewares**: Use `@server.middleware` to intercept calls before and after tool execution (e.g., for rate limiting, auth verification, or custom metrics).
