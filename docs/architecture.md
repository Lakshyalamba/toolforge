# Architecture

MCPToolForge encapsulates the protocol details of the Model Context Protocol (MCP) Python SDK, providing clean, developer-friendly interfaces.

```text
    Client (Claude, etc.)
            │
            ▼ (JSON-RPC over STDIO)
     MCP Transport
            │
            ▼
     MCP Adapter Layer
            │
    ┌───────┴───────┐
    ▼ (Middleware)  ▼ (Direct)
  Tools          Resources & Prompts
```

## Core Components

### 1. MCPServer
The main application class that coordinates the server lifecycle, registry setups, and runs the transport loops.

### 2. Tools Registry
Stores registered `@server.tool` definitions. Introspects Python function signatures to generate valid JSON Schema definitions automatically.

### 3. Resource Registry
Registers `@server.resource` handlers to serve static or dynamic content under specific URI schemes (e.g., `config://app`).

### 4. Prompt Registry
Registers `@server.prompt` templates allowing clients to discover and retrieve preset prompt instructions.

### 5. Middleware & Hook Pipelines
Wraps tool execution with logging, timing, or authentication middlewares. Supports `@server.on_startup` and `@server.on_shutdown` hooks.
