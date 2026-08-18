# ToolForge

A developer-friendly Python framework for creating and exposing Model Context Protocol (MCP) tools with minimal boilerplate.

## Project Status

**Active Development**

ToolForge now supports exposing registered Python tools as Model Context Protocol (MCP) tools using the standard low-level `Server` over the process's standard input/output (stdio) streams. Network and SSE transports are planned for upcoming stages.

## What ToolForge Solves

 Exposing Python code as tools for AI/LLM systems currently requires complex boilerplate code or manual JSON Schema definitions. ToolForge simplifies this by:
1. Inferring tool schemas automatically from Python function signatures and type annotations.
2. Managing the registry, validation, and lifecycle of registered callables.
3. Decoupling tool execution logic from specific transports.

## Planned Architecture

ToolForge separates concerns into distinct modules:
- **`MCPServer`**: Core API server orchestration.
- **`registry`**: Tracks and maps tools to callables.
- **`schema`**: Automatically converts function signatures to JSON schemas.
- **`execution`**: Safely executes tools, handling sync and async functions.
- **`transports`**: Implements JSON-RPC over stdio, SSE, or custom transport protocols.

## Installation

```bash
pip install toolforge
```

## Basic Usage

```python
from toolforge import MCPServer

server = MCPServer("my-tools")

@server.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

## Creating a Tool

To register a tool on an `MCPServer`, use the `@server.tool` decorator:

```python
from toolforge import MCPServer

server = MCPServer("demo")

@server.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

Internally, ToolForge handles this registration seamlessly:

```text
  Python function
         ↓
   @server.tool
         ↓
   Tool metadata (name, docstring, parameters, return type)
         ↓
    ToolRegistry
```

> [!NOTE]
> ToolForge is in early development. Standard Model Context Protocol (MCP) transport support (such as stdio JSON-RPC or Server-Sent Events) is upcoming. Currently, registration and tool introspection function locally.

## Automatic Schema Generation

ToolForge automatically derives JSON Schema inputs from standard Python type annotations and default values. Developers do not need to write JSON schemas manually.

For example, given this tool:

```python
@server.tool
def search(query: str, limit: int = 10):
    """Search information."""
    ...
```

ToolForge dynamically generates the corresponding input schema:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string"
    },
    "limit": {
      "type": "integer",
      "default": 10
    }
  },
  "required": ["query"]
}
```

This ensures full type safety and seamless integration with MCP clients out-of-the-box.

## Runtime Validation

ToolForge verifies incoming arguments against the generated tool schemas during execution. If invalid, missing, or unexpected arguments are supplied, the error is isolated and returned cleanly without crashing the server.

```text
  Tool registration
         ↓
  Schema generation
         ↓
  Runtime argument validation (type safety checks)
         ↓
  Tool execution (sync or async)
```

For example:
- **Valid Call**: `add(10, 20)` $\to$ returns `30`.
- **Missing Parameter**: Calling `add(10)` $\to$ returns error: `Tool 'add': missing required parameter 'b'.`
- **Invalid Parameter Type**: Calling `add("hello", 20)` $\to$ returns error: `Tool 'add': parameter 'a' expected integer, received str.`
- **Unexpected Parameter**: Calling `add(10, 20, c=30)` $\to$ returns error: `Tool 'add': unexpected parameter 'c'.`


## MCP Server

ToolForge handles the translation and registration of local Python callables as standard Model Context Protocol (MCP) tools:

```text
 @server.tool
       ↓
 Tool registration (ToolRegistry)
       ↓
 Schema generation (input_schema)
       ↓
 MCP tool exposure (MCPAdapter maps schema and name)
       ↓
 Stdio server execution (MCPServer.run() processes requests)
```

### Run locally

An example MCP server exposing `add` and `greet` tools is included at [basic_mcp_server.py](file:///Users/lakshyachoudhary/My%20Projects/toolforge/examples/basic_mcp_server.py).

To start this server over the standard input/output (STDIO) transport:

```bash
python examples/basic_mcp_server.py
```

You can connect to this server using any standard MCP client or command-line inspector (such as `@modelcontextprotocol/inspector`).

## End-to-End MCP Verification

ToolForge's MCP implementation is verified end-to-end through automated integration tests that simulate a complete client-server conversation:

1. **MCP Initialization Handshake**: Establishes protocol compatibility and negotiates capabilities.
2. **Tool Discovery (list_tools)**: Allows client to discover registered tools (`add`, `greet`, `failing_tool`, `get_info`), mapping schemas, types, and descriptions accurately.
3. **Tool Invocations (call_tool)**: Runs synchronous/asynchronous callables natively and returns outputs (structured data for dict results, and TextContent blocks for other primitive returns).
4. **Error Isolation**: Confirms execution exceptions or invalid parameters return cleanly as error results (`is_error=True`) without crashing the active server.

To execute the verification suite:

```bash
python3 -m pytest tests/integration/test_mcp_server.py
```


## Command-Line Interface (CLI)

ToolForge includes a developer-friendly command-line interface to create, run, and inspect servers with minimal setup:

### Installation

Ensure the package is installed:
```bash
pip install toolforge
```

### Usage and Help

To view all available commands:
```bash
toolforge --help
```

### Initialize a Project

Create a new working MCP server template in a specified directory:
```bash
toolforge init my-server
```
This generates the following folder structure:
```text
my-server/
├── server.py
├── pyproject.toml
├── README.md
└── .gitignore
```
*Note: If files already exist in the target directory, `init` will fail safely to prevent accidental overwrites. Use `--force` to overwrite.*

### List Tools

Display all registered tools on a server file without starting the transport loops:
```bash
toolforge list --file server.py
```

### Inspect Server and Tool Schemas

Inspect general server details:
```bash
toolforge inspect --file server.py
```

Inspect details and input schemas of a specific tool:
```bash
toolforge inspect add --file server.py
```

### Run Server

Start the MCP transport loops for standard input/output (STDIO) transport:
```bash
toolforge run --file server.py
```


## Development Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

3. Install development dependencies:
   ```bash
   pip install pytest ruff
   ```

## Testing Command

To run the unit tests:
```bash
pytest
```

## Roadmap

- [x] Foundation architecture layout and schema generation
- [x] Implement local stdio JSON-RPC transport
- [x] Add CLI interface for installing and executing servers
- [x] Implement robust runtime argument validation and tool execution
- [ ] Implement SSE transport for network integration
- [ ] Integration with MCP-compliant AI environments (e.g. Claude Desktop)
