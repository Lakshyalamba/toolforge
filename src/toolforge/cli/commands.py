import json
import os
import sys
from pathlib import Path
from typing import Any

from toolforge.errors import ConfigurationError
from toolforge.project import Project, load_server_from_file, load_server_from_project


def resolve_server_instance(file_path: str | None) -> tuple[Any, Project | None]:
    """Resolve the MCPServer instance and the discovered Project config context."""
    if file_path is not None:
        server = load_server_from_file(Path(file_path))
        try:
            project = Project.discover()
        except Exception:
            project = None
        return server, project

    try:
        project = Project.discover()
        server = load_server_from_project(project)
        return server, project
    except ConfigurationError as e:
        # If configuration error was raised (like invalid entrypoint or transport), bubble it up
        raise e
    except Exception:
        # Fallback to default "server.py" in current working directory
        default_path = Path.cwd() / "server.py"
        server = load_server_from_file(default_path)
        return server, None


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

[tool.toolforge]
name = "{project_name}"
entrypoint = "server.py"
transport = "stdio"
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


def run_command(file_path: str | None) -> None:
    """Execute the discovered MCPServer instance loop."""
    try:
        server, _ = resolve_server_instance(file_path)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    server.run()


def list_command(file_path: str | None) -> None:
    """Print all registered tools, resources, and prompts in the project.

    Does so without booting the server.
    """
    try:
        server, _ = resolve_server_instance(file_path)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"ToolForge Server: {server.name}")
    print()
    print("Tools")
    print("─────────────────────────")
    for tool in server.tools:
        desc = tool.description or ""
        first_line = desc.split("\n")[0] if desc else ""
        print(f"{tool.name:<9} {first_line}")

    resources = server.list_resources()
    if resources:
        print()
        print("Resources")
        print("─────────────────────────")
        for res in resources:
            desc = res.description or ""
            first_line = desc.split("\n")[0] if desc else ""
            print(f"{res.uri:<15} {first_line}")

    prompts = server.list_prompts()
    if prompts:
        print()
        print("Prompts")
        print("─────────────────────────")
        for pr in prompts:
            desc = pr.description or ""
            first_line = desc.split("\n")[0] if desc else ""
            print(f"{pr.name:<15} {first_line}")


def inspect_command(file_path: str | None, tool_name: str | None = None) -> None:
    """Inspect the server configuration, specific tool, resource, or prompt detail."""
    try:
        server, project = resolve_server_instance(file_path)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if tool_name is None:
        print("ToolForge Project")
        print("─────────────────────────")
        if project is not None:
            print(f"Name: {project.config.name}")
            print(f"Root: {project.root}")
            print(f"Entrypoint: {project.config.entrypoint}")
            print(f"Transport: {project.config.transport}")
        else:
            print(f"Name: {server.name}")
            print(f"Root: {Path.cwd()}")
            print(f"Entrypoint: {Path(file_path or 'server.py').name}")
            print("Transport: stdio")
        print()
        print("Tools")
        print("─────────────────────────")
        for tool in server.tools:
            print(tool.name)

        resources = server.list_resources()
        if resources:
            print()
            print("Resources")
            print("─────────────────────────")
            for res in resources:
                print(res.uri)

        prompts = server.list_prompts()
        if prompts:
            print()
            print("Prompts")
            print("─────────────────────────")
            for pr in prompts:
                print(pr.name)
    else:
        # 1. Try to find a matching tool
        target_tool = None
        for tool in server.tools:
            if tool.name == tool_name:
                target_tool = tool
                break

        if target_tool is not None:
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
            return

        # 2. Try to find a matching resource
        target_resource = None
        for res in server.list_resources():
            if res.uri == tool_name:
                target_resource = res
                break

        if target_resource is not None:
            print(f"Resource: {target_resource.uri}")
            print()
            print(f"  Name: {target_resource.name}")
            print(f"  MIME: {target_resource.mime_type or 'unspecified'}")
            print(f"  Description: {target_resource.description or ''}")
            return

        # 3. Try to find a matching prompt
        target_prompt = None
        for pr in server.list_prompts():
            if pr.name == tool_name:
                target_prompt = pr
                break

        if target_prompt is not None:
            print(f"Prompt: {target_prompt.name}")
            print()
            print("Description:")
            print(target_prompt.description or "")
            print()
            print("Arguments:")
            for p_name, p in target_prompt.parameters.items():
                required_str = "yes" if p.required else "no"
                type_name = getattr(p.annotation, "__name__", str(p.annotation))
                if type_name == "str":
                    type_name = "string"
                print(f"  {p_name}")
                print(f"    type: {type_name}")
                print(f"    required: {required_str}")
                print()
            return

        print(
            f"Error: tool, resource, or prompt '{tool_name}' is not registered.",
            file=sys.stderr,
        )
        sys.exit(1)
