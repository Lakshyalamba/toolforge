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
    """Verify complete flow: client handshake, tool listing, calling, error handling."""
    server = MCPServer("test-integration-server")

    # Define tools using actual ToolForge decorators
    @server.tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @server.tool
    def greet(name: str) -> str:
        """Greet a user."""
        return f"Hello, {name}"

    @server.tool
    def failing_tool() -> None:
        """Tool that intentionally fails."""
        raise RuntimeError("intentional test failure")

    @server.tool
    def get_info() -> dict:
        """Get structured info."""
        return {"status": "ok"}

    # Create memory streams for bidirectional connection
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
            # 1. MCP Initialization
            await session.initialize()

            # 2. Tool Discovery Test
            tools_result = await session.list_tools()
            tools_list = tools_result.tools
            assert len(tools_list) == 4

            tool_names = {tool.name for tool in tools_list}
            assert "add" in tool_names
            assert "greet" in tool_names
            assert "failing_tool" in tool_names
            assert "get_info" in tool_names

            # Verify name, description, schema
            add_tool = next(tool for tool in tools_list if tool.name == "add")
            assert add_tool.description == "Add two numbers."
            assert add_tool.input_schema["properties"]["a"] == {"type": "integer"}
            assert add_tool.input_schema["properties"]["b"] == {"type": "integer"}
            assert set(add_tool.input_schema["required"]) == {"a", "b"}

            # 3. Tool Invocation Test - add(10, 20) -> 30
            add_res = await session.call_tool("add", {"a": 10, "b": 20})
            assert not add_res.is_error
            assert add_res.content[0].text == "30"

            # 4. Tool Invocation Test - greet("Lakshya") -> "Hello, Lakshya"
            greet_res = await session.call_tool("greet", {"name": "Lakshya"})
            assert not greet_res.is_error
            assert greet_res.content[0].text == "Hello, Lakshya"

            # 5. Multiple Tool Test - get_info (structured dictionary)
            info_res = await session.call_tool("get_info")
            assert not info_res.is_error
            assert info_res.structured_content == {"status": "ok"}

            # 6. Unknown Tool Test - nonexistent_tool raises MCPError
            with pytest.raises(MCPError) as exc_info:
                await session.call_tool("nonexistent_tool")
            assert exc_info.value.error.code == -32601
            assert "not registered" in exc_info.value.error.message

            # 7. Invalid Argument Test - call add without required parameter b
            missing_arg_res = await session.call_tool("add", {"a": 10})
            assert missing_arg_res.is_error is True
            assert "missing required parameter 'b'" in missing_arg_res.content[0].text

            # Recover check
            add_rec1 = await session.call_tool("add", {"a": 10, "b": 20})
            assert not add_rec1.is_error
            assert add_rec1.content[0].text == "30"

            # 8. Invalid Argument Type Test - call add with a="hello"
            invalid_type_res = await session.call_tool("add", {"a": "hello", "b": 20})
            assert invalid_type_res.is_error is True
            assert "expected integer, received str" in invalid_type_res.content[0].text

            # Recover check
            add_rec2 = await session.call_tool("add", {"a": 10, "b": 20})
            assert not add_rec2.is_error
            assert add_rec2.content[0].text == "30"

            # 9. Unexpected Argument Test - call add with extra c=30
            unexpected_arg_res = await session.call_tool("add", {"a": 10, "b": 20, "c": 30})
            assert unexpected_arg_res.is_error is True
            assert "unexpected parameter 'c'" in unexpected_arg_res.content[0].text

            # Recover check
            add_rec3 = await session.call_tool("add", {"a": 10, "b": 20})
            assert not add_rec3.is_error
            assert add_rec3.content[0].text == "30"

            # 10. Tool Execution Error Test - call failing_tool
            failing_res = await session.call_tool("failing_tool")
            assert failing_res.is_error is True
            assert "intentional test failure" in failing_res.content[0].text

            # 11. Server Liveness: Confirm we can still call add successfully after errors
            add_recovery_res = await session.call_tool("add", {"a": 5, "b": 5})
            assert not add_recovery_res.is_error
            assert add_recovery_res.content[0].text == "10"

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        await anyio.sleep(0.1)
        await run_client()
        await client_read_send.aclose()
        await server_read_send.aclose()
