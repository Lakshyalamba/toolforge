import logging
import sys

import mcp.types as t
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from toolforge.mcp.adapter import MCPAdapter
from toolforge.registry import ToolRegistry

logger = logging.getLogger("toolforge")
handler = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class MCPServerRunner:
    """Responsible for running a ToolForge registry over MCP Stdio transport."""

    def __init__(self, server_name: str, registry: ToolRegistry) -> None:
        self.server_name = server_name
        self.registry = registry
        self.adapter = MCPAdapter(self.registry)

    async def run_async(self) -> None:
        """Asynchronously start the stdio server."""
        mcp_server = Server(self.server_name)

        # Register request handlers
        mcp_server.add_request_handler(
            "tools/list",
            t.PaginatedRequestParams,
            self.adapter.handle_list_tools,
        )
        mcp_server.add_request_handler(
            "tools/call",
            t.CallToolRequestParams,
            self.adapter.handle_call_tool,
        )

        init_options = InitializationOptions(
            server_name=self.server_name,
            server_version="0.1.0",
            capabilities=t.ServerCapabilities(
                tools=t.ToolsCapability(list_changed=False)
            ),
        )

        logger.info(f"Starting MCP stdio transport loop for '{self.server_name}'...")
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                initialization_options=init_options,
                raise_exceptions=False,
            )
