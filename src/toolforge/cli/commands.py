import json
import os
import sys
from typing import Any

from toolforge.errors import ToolForgeError


def load_server(file_path: str) -> Any:
    """Safely load the MCPServer instance from the specified file path."""
    if not os.path.exists(file_path):
        print(f"Error: '{file_path}' was not found.", file=sys.stderr)
        sys.exit(1)

    try:
        import importlib.util

        abs_path = os.path.abspath(file_path)
        module_name = "toolforge_user_server"

        spec = importlib.util.spec_from_file_location(module_name, abs_path)
        if spec is None or spec.loader is None:
            print(f"Error: Could not load file '{file_path}'.", file=sys.stderr)
            sys.exit(1)

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        from toolforge import MCPServer

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, MCPServer):
                return attr

        print(f"Error: No MCPServer instance found in '{file_path}'.", file=sys.stderr)
        sys.exit(1)
    except ToolForgeError as e:
        print(f"Error loading server: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error loading server: {e}", file=sys.stderr)
        sys.exit(1)


def init_command(directory: str, force: bool = False) -> None:
    """Initialize a new ToolForge project directory with a working MCPServer template."""
    target_dir = os.path.abspath(directory)
    project_name = os.path.basename(target_dir.rstrip(os.sep)) or "my-server"

    if os.path.exists(target_dir) and os.listdir(target_dir):
        conflicts = [
            f
            for f in ["server.py", "pyproject.toml", "README.md", ".gitignore"]
            if os.path.exists(os.path.join(target_dir, f))
        ]
        if conflicts and not force:
            print(
                f"Error: Destination contains conflicts (e.g. '{conflicts[0]}' already exists). "
                "Use --force to overwrite.",
                file=sys.stderr,
            )
            sys.exit(1)

    os.makedirs(target_dir, exist_ok=True)

    server_content = f"""from toolforge import MCPServer

server = MCPServer("{project_name}")

@server.tool
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

if __name__ == "__main__":
    server.run()
"""

    pyproject_content = f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
dependencies = [
    "toolforge",
]
"""

    readme_content = f"""# {project_name}

A ToolForge MCP tool server.

## Running

```bash
python server.py
```
"""

    gitignore_content = """__pycache__/
.venv/
*.pyc
"""

    with open(os.path.join(target_dir, "server.py"), "w") as f:
        f.write(server_content)
    with open(os.path.join(target_dir, "pyproject.toml"), "w") as f:
        f.write(pyproject_content)
    with open(os.path.join(target_dir, "README.md"), "w") as f:
        f.write(readme_content)
    with open(os.path.join(target_dir, ".gitignore"), "w") as f:
        f.write(gitignore_content)

    print(f"Initialized ToolForge project in '{target_dir}'", file=sys.stderr)


def run_command(file_path: str) -> None:
    """Execute the discovered MCPServer instance loop."""
    server = load_server(file_path)
    server.run()


def list_command(file_path: str) -> None:
    """Print all registered tools in the project without booting the server."""
    server = load_server(file_path)
    print(f"ToolForge Server: {server.name}")
    print()
    print("Tools")
    print("─────────────────────────")
    for tool in server.tools:
        desc = tool.description or ""
        first_line = desc.split("\n")[0] if desc else ""
        print(f"{tool.name:<9} {first_line}")


def inspect_command(file_path: str, tool_name: str | None = None) -> None:
    """Inspect the server configuration or specific tool schema detail."""
    server = load_server(file_path)
    if tool_name is None:
        print("Server")
        print("─────────────────────")
        print(f"Name: {server.name}")
        print()
        print("Transport")
        print("─────────────────────")
        print("stdio")
        print()
        print("Tools")
        print("─────────────────────")
        for tool in server.tools:
            print(tool.name)
    else:
        target_tool = None
        for tool in server.tools:
            if tool.name == tool_name:
                target_tool = tool
                break
        if target_tool is None:
            print(f"Error: tool '{tool_name}' is not registered.", file=sys.stderr)
            sys.exit(1)

        print(f"Tool: {target_tool.name}")
        print()
        print("Description:")
        print(target_tool.description or "")
        print()
        print("Parameters:")
        print()
        for p_name, p in target_tool.parameters.items():
            required_str = "yes" if p.required else "no"
            type_name = getattr(p.annotation, "__name__", str(p.annotation))
            print(f"{p_name}")
            print(f"  type: {type_name}")
            print(f"  required: {required_str}")
            print()
        print("Input Schema:")
        print(json.dumps(target_tool.input_schema, indent=4))
