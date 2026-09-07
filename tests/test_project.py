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


def test_dspy_config_defaults() -> None:
    """Verify DSPyConfig defaults."""
    from toolforge.config import DSPyConfig

    cfg = DSPyConfig()
    assert cfg.enabled is False
    assert cfg.model is None
    assert cfg.temperature == 0.0
    assert cfg.confidence_threshold == 0.6
    assert cfg.compiled_program_path is None
    assert cfg.optimization.enabled is False
    assert cfg.optimization.cache_dir == ".toolforge/intelligence"


def test_dspy_config_validations() -> None:
    """Verify DSPyConfig raises InvalidConfigurationError on invalid values."""
    from toolforge.config import DSPyConfig, DSPyOptimizationConfig

    # 1. Invalid enabled type
    with pytest.raises(InvalidConfigurationError, match=r"dspy.enabled.*boolean"):
        DSPyConfig(enabled="true")  # type: ignore[arg-type]

    # 2. Invalid model type or empty
    with pytest.raises(InvalidConfigurationError, match=r"dspy.model.*string"):
        DSPyConfig(model="")
    with pytest.raises(InvalidConfigurationError, match=r"dspy.model.*string"):
        DSPyConfig(model=123)  # type: ignore[arg-type]

    # 3. Invalid temperature
    with pytest.raises(InvalidConfigurationError, match=r"dspy.temperature.*number"):
        DSPyConfig(temperature="hot")  # type: ignore[arg-type]
    with pytest.raises(InvalidConfigurationError, match=r"dspy.temperature.*number"):
        DSPyConfig(temperature=True)  # type: ignore[arg-type]
    with pytest.raises(InvalidConfigurationError, match=r"between 0.0 and 2.0"):
        DSPyConfig(temperature=-0.1)
    with pytest.raises(InvalidConfigurationError, match=r"between 0.0 and 2.0"):
        DSPyConfig(temperature=2.1)

    # 4. Invalid confidence_threshold
    with pytest.raises(InvalidConfigurationError, match=r"dspy.confidence_threshold.*number"):
        DSPyConfig(confidence_threshold="high")  # type: ignore[arg-type]
    with pytest.raises(InvalidConfigurationError, match=r"dspy.confidence_threshold.*number"):
        DSPyConfig(confidence_threshold=False)  # type: ignore[arg-type]
    with pytest.raises(InvalidConfigurationError, match=r"between 0.0 and 1.0"):
        DSPyConfig(confidence_threshold=-0.01)
    with pytest.raises(InvalidConfigurationError, match=r"between 0.0 and 1.0"):
        DSPyConfig(confidence_threshold=1.01)

    # 5. Invalid compiled_program_path
    with pytest.raises(InvalidConfigurationError, match=r"dspy.compiled_program_path.*string"):
        DSPyConfig(compiled_program_path="")

    # 6. Invalid optimization sub-table
    with pytest.raises(InvalidConfigurationError, match=r"dspy.optimization"):
        DSPyConfig(optimization="invalid")  # type: ignore[arg-type]

    with pytest.raises(InvalidConfigurationError, match=r"dspy.optimization.enabled.*boolean"):
        DSPyOptimizationConfig(enabled="yes")  # type: ignore[arg-type]

    with pytest.raises(InvalidConfigurationError, match=r"dspy.optimization.cache_dir.*string"):
        DSPyOptimizationConfig(cache_dir="")


def test_project_discovery_dspy_valid() -> None:
    """Verify pyproject.toml parsing of [tool.toolforge.dspy] and optimization tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text(
            "[tool.toolforge]\n"
            'name = "ai-project"\n'
            'entrypoint = "server.py"\n'
            "\n"
            "[tool.toolforge.dspy]\n"
            "enabled = true\n"
            'model = "openai/gpt-4o-mini"\n'
            "temperature = 0.3\n"
            "confidence_threshold = 0.8\n"
            'compiled_program_path = "models/optimized.json"\n'
            "\n"
            "[tool.toolforge.dspy.optimization]\n"
            "enabled = true\n"
            'cache_dir = ".custom_cache"\n'
        )

        project = Project.discover(start_dir=root)
        assert project.config.name == "ai-project"
        assert project.config.dspy.enabled is True
        assert project.config.dspy.model == "openai/gpt-4o-mini"
        assert project.config.dspy.temperature == 0.3
        assert project.config.dspy.confidence_threshold == 0.8
        assert project.config.dspy.compiled_program_path == "models/optimized.json"
        assert project.config.dspy.optimization.enabled is True
        assert project.config.dspy.optimization.cache_dir == ".custom_cache"


def test_project_discovery_dspy_rejects_api_keys() -> None:
    """Verify pyproject.toml rejects attempts to store API keys and secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        pyproject = root / "pyproject.toml"
        pyproject.write_text(
            "[tool.toolforge]\n"
            'name = "leaky-project"\n'
            "\n"
            "[tool.toolforge.dspy]\n"
            "enabled = true\n"
            'api_key = "sk-123456789"\n'
        )

        with pytest.raises(InvalidConfigurationError, match="Do not store API keys or secrets"):
            Project.discover(start_dir=root)


def test_toolforge_config_create_mapper() -> None:
    """Verify ToolForgeConfig.create_mapper returns appropriate mapper based on dspy.enabled."""
    from toolforge.intelligence import DSPyToolMapper, StaticToolMapper

    # 1. Disabled (default)
    config_disabled = ToolForgeConfig(name="test")
    mapper_disabled = config_disabled.create_mapper()
    assert isinstance(mapper_disabled, StaticToolMapper)

    # 2. Enabled
    config_enabled = ToolForgeConfig(
        name="test",
        dspy={"enabled": True, "confidence_threshold": 0.85},  # type: ignore[arg-type]
    )
    mapper_enabled = config_enabled.create_mapper()
    assert isinstance(mapper_enabled, DSPyToolMapper)
    assert mapper_enabled.confidence_threshold == 0.85
