import importlib.util
import sys
import tomllib
from pathlib import Path

from mcptoolforge.config import MCPToolForgeConfig
from mcptoolforge.errors import (
    EntrypointNotFoundError,
    InvalidConfigurationError,
    ProjectNotFoundError,
)
from mcptoolforge.server import MCPServer


class Project:
    """Represents a discovered MCPToolForge project and its configuration."""

    def __init__(self, root: Path, pyproject_path: Path, config: MCPToolForgeConfig):
        self.root = root
        self.pyproject_path = pyproject_path
        self.config = config

    @classmethod
    def discover(cls, start_dir: Path | None = None) -> "Project":
        """Search up directory tree starting from start_dir for pyproject.toml."""
        current = Path(start_dir or Path.cwd()).resolve()

        while True:
            pyproject_file = current / "pyproject.toml"
            if pyproject_file.is_file():
                try:
                    with open(pyproject_file, "rb") as f:
                        data = tomllib.load(f)
                except Exception as e:
                    raise InvalidConfigurationError(
                        f"Failed to parse TOML in '{pyproject_file}': {e}"
                    ) from e

                # Extract [tool.mcptoolforge] section
                tool_data = data.get("tool", {})
                if "mcptoolforge" not in tool_data:
                    raise ProjectNotFoundError(
                        "MCPToolForge configuration '[tool.mcptoolforge]' not found "
                        f"in '{pyproject_file}'."
                    )

                tf_section = tool_data["mcptoolforge"]
                if not isinstance(tf_section, dict):
                    raise InvalidConfigurationError(
                        "Section '[tool.mcptoolforge]' "
                        f"in '{pyproject_file}' must be a table/dictionary."
                    )

                if "name" not in tf_section:
                    raise InvalidConfigurationError(
                        "Required configuration field 'name' is missing "
                        f"from '[tool.mcptoolforge]' in '{pyproject_file}'."
                    )

                config = MCPToolForgeConfig(
                    name=tf_section["name"],
                    entrypoint=tf_section.get("entrypoint", "server.py"),
                    transport=tf_section.get("transport", "stdio"),
                )

                return cls(
                    root=current,
                    pyproject_path=pyproject_file,
                    config=config,
                )

            # Move up to parent directory
            parent = current.parent
            if parent == current:
                raise ProjectNotFoundError(
                    "Could not find a pyproject.toml file in parent directories."
                )
            current = parent


def load_server_from_project(project: Project) -> MCPServer:
    """Safely load and import the MCPServer instance from the project configuration."""
    entrypoint_path = (project.root / project.config.entrypoint).resolve()
    return load_server_from_file(entrypoint_path)


def load_server_from_file(file_path: Path) -> MCPServer:
    """Safely load and import the MCPServer instance from a specific file path."""
    if not file_path.exists():
        raise EntrypointNotFoundError(f"MCPToolForge entrypoint '{file_path.name}' was not found.")

    if not file_path.is_file() or file_path.suffix != ".py":
        raise InvalidConfigurationError(
            f"MCPToolForge entrypoint '{file_path.name}' is not a Python file."
        )

    try:
        module_name = "mcptoolforge_user_server"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise InvalidConfigurationError(
                f"Failed to load spec for entrypoint '{file_path.name}'."
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        raise InvalidConfigurationError(
            f"Failed to execute entrypoint module '{file_path.name}': {e}"
        ) from e

    # Find the expected server object in the loaded module variables
    server_vars = {}
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, MCPServer):
            server_vars[attr_name] = attr

    # 1. Enforce naming convention first
    if "server" in server_vars:
        return server_vars["server"]

    # 2. Check for multiple instances (ambiguity)
    if len(server_vars) > 1:
        raise InvalidConfigurationError(
            f"Multiple MCPServer instances found in '{file_path.name}', "
            f"but none are named 'server'. Ambiguity detected: {list(server_vars.keys())}."
        )

    # 3. No instance or naming convention mismatch
    raise InvalidConfigurationError(
        f"Entry point '{file_path.name}' does not define a MCPToolForge MCPServer named 'server'."
    )
