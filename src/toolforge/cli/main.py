import argparse
import importlib.metadata
import sys

from toolforge.cli.commands import (
    benchmark_command,
    evaluate_command,
    init_command,
    inspect_command,
    list_command,
    map_command,
    optimize_command,
    run_command,
)


def get_version() -> str:
    """Retrieve authoritative package version or fallback to 0.1.0."""
    try:
        return importlib.metadata.version("toolforge")
    except Exception:
        return "0.1.0"


def main() -> None:
    """Entrypoint parsing CLI commands."""
    parser = argparse.ArgumentParser(
        prog="toolforge",
        description="ToolForge\nBuild MCP-ready tools with minimal boilerplate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"toolforge {get_version()}",
        help="Show version information.",
    )

    subparsers = parser.add_subparsers(dest="command", title="Available commands")

    # 1. init subcommand
    init_parser = subparsers.add_parser("init", help="Initialize a new ToolForge project.")
    init_parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to initialize the project in. (default: current directory)",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing files in the destination directory.",
    )

    # 2. run subcommand
    run_parser = subparsers.add_parser("run", help="Start the ToolForge MCP server.")
    run_parser.add_argument(
        "--file",
        default=None,
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )

    # 3. list subcommand
    list_parser = subparsers.add_parser("list", help="List registered tools locally.")
    list_parser.add_argument(
        "--file",
        default=None,
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )

    # 4. inspect subcommand
    inspect_parser = subparsers.add_parser(
        "inspect", help="Inspect server or specific tool details."
    )
    inspect_parser.add_argument(
        "tool_name",
        nargs="?",
        default=None,
        help="Name of the specific tool to inspect.",
    )
    inspect_parser.add_argument(
        "--file",
        default=None,
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )

    # 5. map subcommand
    map_parser = subparsers.add_parser(
        "map", help="Map tools and inspect semantic understanding and classification."
    )
    map_parser.add_argument(
        "tool_name",
        nargs="?",
        default=None,
        help="Optional specific tool name to map.",
    )
    map_parser.add_argument(
        "--file",
        default=None,
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )
    map_parser.add_argument(
        "--json",
        action="store_true",
        help="Output mapping results as JSON.",
    )

    # 6. evaluate subcommand
    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate semantic tool mapping performance against a benchmark dataset.",
    )
    eval_parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the benchmark dataset file (.json or .jsonl).",
    )
    eval_parser.add_argument(
        "--file",
        default=None,
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )
    eval_parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Confidence/quality score threshold to pass an example (default: 0.7).",
    )
    eval_parser.add_argument(
        "--json",
        action="store_true",
        help="Output evaluation results as JSON.",
    )

    # 7. optimize subcommand
    opt_parser = subparsers.add_parser(
        "optimize",
        help="Compile and optimize semantic tool mapping using DSPy teleprompters.",
    )
    opt_parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the training dataset file (.json or .jsonl).",
    )
    opt_parser.add_argument(
        "--output",
        default=None,
        help="Destination path for the compiled program artifact (.json).",
    )
    opt_parser.add_argument(
        "--valset",
        default=None,
        help="Optional path to a validation dataset file (.json or .jsonl).",
    )
    opt_parser.add_argument(
        "--file",
        default=None,
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )

    # 8. benchmark subcommand
    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Run quantitative side-by-side benchmark comparing Baseline vs DSPy tool mapping.",
    )
    bench_parser.add_argument(
        "--dataset",
        default=None,
        help="Path to custom benchmark dataset (.json or .jsonl). Defaults to 10-tool dataset.",
    )
    bench_parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path to save machine-readable JSON results.",
    )
    bench_parser.add_argument(
        "--output-csv",
        default=None,
        help="Optional path to save machine-readable CSV results.",
    )
    bench_parser.add_argument(
        "--file",
        default=None,
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        init_command(args.directory, args.force)
    elif args.command == "run":
        run_command(args.file)
    elif args.command == "list":
        list_command(args.file)
    elif args.command == "inspect":
        inspect_command(args.file, args.tool_name)
    elif args.command == "map":
        map_command(args.file, args.tool_name, args.json)
    elif args.command == "evaluate":
        evaluate_command(args.dataset, args.file, args.threshold, args.json)
    elif args.command == "optimize":
        optimize_command(args.dataset, args.output, args.valset, args.file)
    elif args.command == "benchmark":
        benchmark_command(args.dataset, args.output_json, args.output_csv, args.file)


if __name__ == "__main__":
    main()
