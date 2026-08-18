import json
import os
import subprocess
import sys
import tempfile


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Helper to run the CLI using sys.executable -m toolforge.cli.main."""
    cmd = [sys.executable, "-m", "toolforge.cli.main", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_cli_help() -> None:
    """Verify --help outputs usage info and exits 0."""
    res = run_cli(["--help"])
    assert res.returncode == 0
    assert "ToolForge" in res.stdout
    assert "init" in res.stdout
    assert "run" in res.stdout
    assert "list" in res.stdout
    assert "inspect" in res.stdout


def test_cli_version() -> None:
    """Verify --version outputs toolforge and package version."""
    res = run_cli(["--version"])
    assert res.returncode == 0
    assert "toolforge 0.1.0" in res.stdout or "toolforge 0.1.0" in res.stderr


def test_cli_init_new_dir() -> None:
    """Verify init creates correct template files in a new directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "my-server")
        res = run_cli(["init", target])
        assert res.returncode == 0
        assert "Initialized ToolForge project" in res.stderr

        # Check generated structure
        assert os.path.exists(os.path.join(target, "server.py"))
        assert os.path.exists(os.path.join(target, "pyproject.toml"))
        assert os.path.exists(os.path.join(target, "README.md"))
        assert os.path.exists(os.path.join(target, ".gitignore"))

        # Verify generated imports and syntax are valid Python
        server_path = os.path.join(target, "server.py")
        syntax_check = subprocess.run(
            [sys.executable, "-m", "py_compile", server_path],
            capture_output=True,
        )
        assert syntax_check.returncode == 0


def test_cli_init_conflict_handling() -> None:
    """Verify init fails if target directory has existing conflicting files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a conflicting file
        conflict_file = os.path.join(tmpdir, "server.py")
        with open(conflict_file, "w") as f:
            f.write("existing content")

        res = run_cli(["init", tmpdir])
        assert res.returncode != 0
        assert "Error: Destination contains conflicts" in res.stderr

        # Verify the file was NOT overwritten
        with open(conflict_file) as f:
            assert f.read() == "existing content"


def test_cli_init_force() -> None:
    """Verify init overwrites conflicting files if --force is set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        conflict_file = os.path.join(tmpdir, "server.py")
        with open(conflict_file, "w") as f:
            f.write("existing content")

        res = run_cli(["init", tmpdir, "--force"])
        assert res.returncode == 0
        assert "Initialized ToolForge project" in res.stderr

        # Verify the file was overwritten with template content
        with open(conflict_file) as f:
            content = f.read()
            assert "MCPServer" in content
            assert "existing content" not in content


def test_cli_list_inspect_missing_server() -> None:
    """Verify list and inspect exit non-zero when target server file is missing."""
    res_list = run_cli(["list", "--file", "nonexistent_server.py"])
    assert res_list.returncode != 0
    assert "ToolForge entrypoint 'nonexistent_server.py' was not found" in res_list.stderr

    res_inspect = run_cli(["inspect", "--file", "nonexistent_server.py"])
    assert res_inspect.returncode != 0
    assert "ToolForge entrypoint 'nonexistent_server.py' was not found" in res_inspect.stderr


def test_cli_list_inspect_success() -> None:
    """Verify list and inspect operations on a valid server.py file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_cli(["init", tmpdir])
        server_py = os.path.join(tmpdir, "server.py")

        # 1. Test list
        res_list = run_cli(["list", "--file", server_py])
        assert res_list.returncode == 0
        assert "ToolForge Server: " in res_list.stdout
        assert "add" in res_list.stdout

        # 2. Test inspect general
        res_inspect = run_cli(["inspect", "--file", server_py])
        assert res_inspect.returncode == 0
        assert "ToolForge Project" in res_inspect.stdout
        assert "stdio" in res_inspect.stdout
        assert "add" in res_inspect.stdout

        # 3. Test inspect specific tool
        res_inspect_tool = run_cli(["inspect", "add", "--file", server_py])
        assert res_inspect_tool.returncode == 0
        assert "Tool: add" in res_inspect_tool.stdout
        assert "Parameters:" in res_inspect_tool.stdout
        assert "Input Schema:" in res_inspect_tool.stdout

        # Verify JSON schema is valid in output
        lines = res_inspect_tool.stdout.split("\n")
        schema_start = lines.index("Input Schema:") + 1
        schema_json = "\n".join(lines[schema_start:])
        schema = json.loads(schema_json)
        assert schema["type"] == "object"
        assert "a" in schema["properties"]

        # 4. Test inspect missing tool
        res_missing_tool = run_cli(["inspect", "nonexistent_tool", "--file", server_py])
        assert res_missing_tool.returncode != 0
        assert "Error: tool 'nonexistent_tool' is not registered" in res_missing_tool.stderr


def test_cli_invalid_project() -> None:
    """Verify CLI error handling when server file exists but has no MCPServer instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_server = os.path.join(tmpdir, "server.py")
        with open(bad_server, "w") as f:
            f.write("# empty server\n")

        res_list = run_cli(["list", "--file", bad_server])
        assert res_list.returncode != 0
        assert "does not define a ToolForge MCPServer named 'server'" in res_list.stderr
