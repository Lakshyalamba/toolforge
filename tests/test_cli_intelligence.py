import json
import os
import subprocess
import sys
import tempfile


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Helper to run the CLI using sys.executable -m toolforge.cli.main."""
    cmd = [sys.executable, "-m", "toolforge.cli.main", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_cli_help_includes_intelligence_commands() -> None:
    res = run_cli(["--help"])
    assert res.returncode == 0
    assert "map" in res.stdout
    assert "evaluate" in res.stdout
    assert "optimize" in res.stdout


def test_cli_map_command() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server_path = os.path.join(tmpdir, "server.py")
        with open(server_path, "w") as f:
            f.write(
                "from toolforge import MCPServer\n"
                "server = MCPServer('test')\n"
                "@server.tool\n"
                "def calculate(a: int) -> int:\n"
                "    '''Calculate square'''\n"
                "    return a * a\n"
            )

        # Standard human-readable output
        res = run_cli(["map", "--file", server_path])
        assert res.returncode == 0
        assert "ToolForge Semantic Mapping" in res.stdout
        assert "calculate" in res.stdout

        # JSON output
        res_json = run_cli(["map", "--file", server_path, "--json"])
        assert res_json.returncode == 0
        data = json.loads(res_json.stdout)
        assert len(data) == 1
        assert data[0]["name"] == "calculate"
        assert data[0]["original_description"] == "Calculate square"

        # Specific tool filtering
        res_tool = run_cli(["map", "calculate", "--file", server_path])
        assert res_tool.returncode == 0
        assert "calculate" in res_tool.stdout

        # Non-existent tool
        res_missing = run_cli(["map", "non_existent", "--file", server_path])
        assert res_missing.returncode != 0
        assert "not registered" in res_missing.stderr


def test_cli_evaluate_command() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server_path = os.path.join(tmpdir, "server.py")
        with open(server_path, "w") as f:
            f.write(
                "from toolforge import MCPServer\n"
                "server = MCPServer('test')\n"
                "@server.tool\n"
                "def ping() -> str:\n"
                "    '''Health check ping'''\n"
                "    return 'pong'\n"
            )

        dataset_path = os.path.join(tmpdir, "dataset.json")
        with open(dataset_path, "w") as f:
            json.dump(
                [
                    {
                        "tool_name": "ping",
                        "description": "Health check ping",
                        "expected_domain": "system",
                        "expected_category": "utility",
                        "expected_risk_level": "safe",
                    }
                ],
                f,
            )

        res = run_cli(["evaluate", "--dataset", dataset_path, "--file", server_path])
        assert res.returncode == 0
        assert "ToolForge Semantic Mapping Evaluation" in res.stdout
        assert "Dataset:" in res.stdout

        # JSON output
        res_json = run_cli(["evaluate", "--dataset", dataset_path, "--file", server_path, "--json"])
        assert res_json.returncode == 0
        data = json.loads(res_json.stdout)
        assert "total" in data
        assert "mean_score" in data
        assert data["total"] == 1


def test_cli_evaluate_missing_dataset() -> None:
    res = run_cli(["evaluate", "--dataset", "/non/existent/dataset.json"])
    assert res.returncode != 0
    assert "Error loading dataset" in res.stderr


def test_cli_optimize_missing_dataset() -> None:
    res = run_cli(["optimize", "--dataset", "/non/existent/dataset.json"])
    assert res.returncode != 0
    assert "Error loading training dataset" in res.stderr
