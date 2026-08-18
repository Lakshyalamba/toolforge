import anyio
import mcp.types as t
import pytest
from mcp import ClientSession
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import MCPError

from toolforge import MCPServer
from toolforge.mcp.server import MCPServerRunner


@pytest.mark.anyio
async def test_mcp_server_flow_verification() -> None:
    server = MCPServer("test-integration-server")

    @server.tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    server_read_send, server_read_rcv = anyio.create_memory_object_stream(20)
    client_read_send, client_read_rcv = anyio.create_memory_object_stream(20)

    runner = MCPServerRunner(server.name, server.registry)
    mcp_server = Server(server.name)
    mcp_server.add_request_handler(
        "tools/list",
        t.PaginatedRequestParams,
        runner.adapter.handle_list_tools,
    )
    mcp_server.add_request_handler(
        "tools/call",
        t.CallToolRequestParams,
        runner.adapter.handle_call_tool,
    )

    init_options = InitializationOptions(
        server_name=server.name,
        server_version="0.1.0",
        capabilities=t.ServerCapabilities(
            tools=t.ToolsCapability(list_changed=False)
        ),
    )

    async def run_server() -> None:
        await mcp_server.run(
            server_read_rcv,
            client_read_send,
            initialization_options=init_options,
            raise_exceptions=True,
        )

    async def run_client() -> None:
        async with ClientSession(client_read_rcv, server_read_send) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            assert len(tools_result.tools) == 1

            add_res = await session.call_tool("add", {"a": 10, "b": 20})
            assert add_res.content[0].text == "30"

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        await anyio.sleep(0.1)
        await run_client()
        await client_read_send.aclose()
        await server_read_send.aclose()
