import argparse
import importlib.metadata
import sys

from toolforge.cli.commands import (
    init_command,
    inspect_command,
    list_command,
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
        default="server.py",
        help="Path to the python file containing the MCPServer instance. (default: server.py)",
    )

    # 3. list subcommand
    list_parser = subparsers.add_parser("list", help="List registered tools locally.")
    list_parser.add_argument(
        "--file",
        default="server.py",
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
        default="server.py",
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


if __name__ == "__main__":
    main()
