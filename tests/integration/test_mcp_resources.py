import anyio
import mcp.types as t
import pytest
from mcp import ClientSession
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import MCPError

from mcptoolforge import MCPServer
from mcptoolforge.mcp.server import MCPServerRunner


@pytest.mark.anyio
async def test_mcp_resources_flow() -> None:
    """Verify MCP Resource handshake, listing, reading, and client error safety."""
    server = MCPServer("test-resources-server")

    @server.resource("config://app", description="App Config", mime_type="application/json")
    def app_config():
        return {"name": "MCPToolForge", "version": "0.1.0"}

    @server.resource("data://text")
    def text_resource():
        return "plain text content"

    @server.resource("data://blob", mime_type="application/octet-stream")
    def blob_resource():
        return b"binary data"

    @server.resource("test://failure")
    def failing_resource():
        raise RuntimeError("intentional failure")

    # Create memory streams for bidirectional connection
    server_read_send, server_read_rcv = anyio.create_memory_object_stream(20)
    client_read_send, client_read_rcv = anyio.create_memory_object_stream(20)

    runner = MCPServerRunner(server.name, server.registry, server=server)
    mcp_server = Server(server.name)

    mcp_server.add_request_handler(
        "resources/list",
        t.PaginatedRequestParams,
        runner.adapter.handle_list_resources,
    )
    mcp_server.add_request_handler(
        "resources/read",
        t.ReadResourceRequestParams,
        runner.adapter.handle_read_resource,
    )

    init_options = InitializationOptions(
        server_name=server.name,
        server_version="0.1.0",
        capabilities=t.ServerCapabilities(
            resources=t.ResourcesCapability(list_changed=False, subscribe=False)
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
            # A. Handshake
            await session.initialize()

            # B. List Resources
            list_res = await session.list_resources()
            assert len(list_res.resources) == 4

            uris = {r.uri for r in list_res.resources}
            assert "config://app" in uris
            assert "data://text" in uris
            assert "data://blob" in uris
            assert "test://failure" in uris

            # C. Verify Resource Details
            app_res = next(r for r in list_res.resources if r.uri == "config://app")
            assert app_res.name == "app_config"
            assert app_res.description == "App Config"
            assert app_res.mime_type == "application/json"

            # D. Read valid JSON resource
            read_json = await session.read_resource("config://app")
            assert len(read_json.contents) == 1
            content = read_json.contents[0]
            assert content.uri == "config://app"
            assert content.mime_type == "application/json"
            assert "MCPToolForge" in content.text

            # E. Read valid text resource
            read_text = await session.read_resource("data://text")
            assert read_text.contents[0].text == "plain text content"

            # F. Read valid binary resource
            read_blob = await session.read_resource("data://blob")
            assert read_blob.contents[0].blob == "YmluYXJ5IGRhdGE="  # base64 for b"binary data"

            # G. Read unknown resource -> raises MCPError
            with pytest.raises(MCPError) as exc_info:
                await session.read_resource("config://unknown")
            assert exc_info.value.error.code == -32601
            assert "is not registered" in exc_info.value.error.message

            # H. Read a failing resource -> raises MCPError
            with pytest.raises(MCPError) as exc_info:
                await session.read_resource("test://failure")
            assert exc_info.value.error.code == -32603
            assert "intentional failure" in exc_info.value.error.message

            # I. Server Remains Alive: read a valid resource after failure
            read_recovery = await session.read_resource("data://text")
            assert read_recovery.contents[0].text == "plain text content"

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        await anyio.sleep(0.1)
        await run_client()
        await client_read_send.aclose()
        await server_read_send.aclose()
