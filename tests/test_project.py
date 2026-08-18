import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from toolforge import (
    EntrypointNotFoundError,
    InvalidConfigurationError,
    Project,
    ProjectNotFoundError,
    ToolForgeConfig,
    load_server_from_project,
)


def test_config_validation() -> None:
    """Verify ToolForgeConfig validations."""
    config = ToolForgeConfig(name="test")
    assert config.name == "test"
    assert config.entrypoint == "server.py"
    assert config.transport == "stdio"

    # Missing name
    with pytest.raises(InvalidConfigurationError) as exc:
        ToolForgeConfig(name="")
    assert "name" in str(exc.value)

    # Missing entrypoint
    with pytest.raises(InvalidConfigurationError) as exc:
        ToolForgeConfig(name="test", entrypoint="")
    assert "entrypoint" in str(exc.value)

    # Non-python entrypoint
    with pytest.raises(InvalidConfigurationError) as exc:
        ToolForgeConfig(name="test", entrypoint="server.txt")
    assert "not a Python file" in str(exc.value)

    # Unsupported transport
    with pytest.raises(InvalidConfigurationError) as exc:
        ToolForgeConfig(name="test", transport="http")
    assert "Only 'stdio' is currently supported" in str(exc.value)


def test_project_discovery_valid() -> None:
    """Verify discovery loader extracts correct values from pyproject.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text(
            '[tool.toolforge]\nname = "test-project"\nentrypoint = "custom_server.py"\n'
        )

        project = Project.discover(start_dir=root)
        assert project.root == root
        assert project.pyproject_path == pyproject
        assert project.config.name == "test-project"
        assert project.config.entrypoint == "custom_server.py"
        assert project.config.transport == "stdio"


def test_project_discovery_missing_toml() -> None:
    """Verify discover raises error if pyproject.toml is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        with pytest.raises(ProjectNotFoundError) as exc:
            Project.discover(start_dir=root)
        assert "pyproject.toml" in str(exc.value)


def test_project_discovery_missing_section() -> None:
    """Verify discover raises error if [tool.toolforge] section is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[project]\nname = "other"\n')
        with pytest.raises(ProjectNotFoundError) as exc:
            Project.discover(start_dir=root)
        assert "[tool.toolforge]" in str(exc.value)


def test_project_discovery_missing_name() -> None:
    """Verify discover raises error if name is missing from section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nentrypoint = "server.py"\n')
        with pytest.raises(InvalidConfigurationError) as exc:
            Project.discover(start_dir=root)
        assert "field 'name' is missing" in str(exc.value)


def test_project_discovery_nested() -> None:
    """Verify discovery climbs parent directories to resolve project root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "nested-test"\n')

        nested = root / "src" / "cli"
        nested.mkdir(parents=True)

        project = Project.discover(start_dir=nested)
        assert project.root == root
        assert project.pyproject_path == pyproject
        assert project.config.name == "nested-test"


def test_load_server_valid() -> None:
    """Verify valid server loader execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "test"\n')

        server_py = root / "server.py"
        server_py.write_text(
            "from toolforge import MCPServer\n"
            'server = MCPServer("nested-server")\n'
            "@server.tool\n"
            "def add(a: int) -> int: return a\n"
        )

        project = Project.discover(start_dir=root)
        server = load_server_from_project(project)
        assert server.name == "nested-server"
        assert len(server.tools) == 1


def test_load_server_missing_file() -> None:
    """Verify missing entrypoint file raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "test"\n')

        project = Project.discover(start_dir=root)
        with pytest.raises(EntrypointNotFoundError) as exc:
            load_server_from_project(project)
        assert "server.py" in str(exc.value)


def test_load_server_missing_server_variable() -> None:
    """Verify entrypoint raises error if server is not exposed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "test"\n')

        server_py = root / "server.py"
        server_py.write_text(
            'from toolforge import MCPServer\nmy_custom_server = MCPServer("no-server-var")\n'
        )

        project = Project.discover(start_dir=root)
        with pytest.raises(InvalidConfigurationError) as exc:
            load_server_from_project(project)
        assert "does not define a ToolForge MCPServer named 'server'" in str(exc.value)


def test_load_server_invalid_object() -> None:
    """Verify entrypoint raises error if server is not an MCPServer instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "test"\n')

        server_py = root / "server.py"
        server_py.write_text('server = "not-an-mcp-server-instance"\n')

        project = Project.discover(start_dir=root)
        with pytest.raises(InvalidConfigurationError) as exc:
            load_server_from_project(project)
        assert "does not define a ToolForge MCPServer named 'server'" in str(exc.value)


def test_load_server_multiple_objects_without_server() -> None:
    """Verify entrypoint raises error if multiple MCPServer instances exist
    and none are named server.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "test"\n')

        server_py = root / "server.py"
        server_py.write_text(
            "from toolforge import MCPServer\n"
            'server1 = MCPServer("s1")\n'
            'server2 = MCPServer("s2")\n'
        )

        project = Project.discover(start_dir=root)
        with pytest.raises(InvalidConfigurationError) as exc:
            load_server_from_project(project)
        assert "Ambiguity detected" in str(exc.value)


def run_cli_cmd(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "toolforge.cli.main", *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def test_cli_list_using_config() -> None:
    """Verify list command successfully resolves tools using discovered config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "test"\n')

        server_py = root / "server.py"
        server_py.write_text(
            "from toolforge import MCPServer\n"
            'server = MCPServer("my-mcp")\n'
            "@server.tool\n"
            "def add(a: int, b: int) -> int:\n"
            '    """Add two numbers."""\n'
            "    return a + b\n"
        )

        res = run_cli_cmd(["list"], cwd=root)
        assert res.returncode == 0
        assert "ToolForge Server: my-mcp" in res.stdout
        assert "add" in res.stdout


def test_cli_inspect_using_config() -> None:
    """Verify inspect command successfully resolves server table using discovered config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text(
            "[tool.toolforge]\n"
            'name = "my-configured-project"\n'
            'entrypoint = "server.py"\n'
            'transport = "stdio"\n'
        )

        server_py = root / "server.py"
        server_py.write_text(
            "from toolforge import MCPServer\n"
            'server = MCPServer("my-mcp")\n'
            "@server.tool\n"
            "def add(a: int, b: int) -> int: return a + b\n"
        )

        res = run_cli_cmd(["inspect"], cwd=root)
        assert res.returncode == 0
        assert "ToolForge Project" in res.stdout
        assert "Name: my-configured-project" in res.stdout
        assert "Root:" in res.stdout
        assert "Entrypoint: server.py" in res.stdout
        assert "Transport: stdio" in res.stdout


def test_cli_inspect_specific_tool_using_config() -> None:
    """Verify inspect specific tool outputs correctly from discovered config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "test"\n')

        server_py = root / "server.py"
        server_py.write_text(
            "from toolforge import MCPServer\n"
            'server = MCPServer("my-mcp")\n'
            "@server.tool\n"
            "def add(a: int, b: int) -> int: return a + b\n"
        )

        res = run_cli_cmd(["inspect", "add"], cwd=root)
        assert res.returncode == 0
        assert "Tool: add" in res.stdout
        assert "Parameters:" in res.stdout
        assert "Input Schema:" in res.stdout

        lines = res.stdout.split("\n")
        schema_start = lines.index("Input Schema:") + 1
        schema_json = "\n".join(lines[schema_start:])
        schema = json.loads(schema_json)
        assert schema["type"] == "object"
        assert "a" in schema["properties"]


def test_cli_init_generates_correct_config() -> None:
    """Verify init subcommand generates [tool.toolforge] properties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        res = run_cli_cmd(["init", "test-project"], cwd=root)
        assert res.returncode == 0

        pyproject = root / "test-project" / "pyproject.toml"
        assert pyproject.is_file()

        content = pyproject.read_text()
        assert "[tool.toolforge]" in content
        assert 'name = "test-project"' in content
        assert 'entrypoint = "server.py"' in content
        assert 'transport = "stdio"' in content


def test_cli_override_precedence() -> None:
    """Verify explicit --file overrides discovered config values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text('[tool.toolforge]\nname = "configured"\nentrypoint = "server.py"\n')

        # Create two server files
        server_py = root / "server.py"
        server_py.write_text(
            'from toolforge import MCPServer\nserver = MCPServer("configured-server")\n'
        )

        other_py = root / "other.py"
        other_py.write_text(
            'from toolforge import MCPServer\nserver = MCPServer("overridden-server")\n'
        )

        # List without override -> uses configured entrypoint (server.py)
        res1 = run_cli_cmd(["list"], cwd=root)
        assert res1.returncode == 0
        assert "ToolForge Server: configured-server" in res1.stdout

        # List with override -> uses CLI --file argument (other.py)
        res2 = run_cli_cmd(["list", "--file", "other.py"], cwd=root)
        assert res2.returncode == 0
        assert "ToolForge Server: overridden-server" in res2.stdout
