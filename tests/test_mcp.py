import anyio
import mcp.types as t
import pytest
from mcp.shared.exceptions import MCPError

from toolforge import MCPServer
from toolforge.mcp.adapter import MCPAdapter


def test_mcp_adapter_mapping_and_errors() -> None:
    """Test that MCPServer registry integrates and maps cleanly to MCP adapter."""
    server = MCPServer("test-adapter")

    @server.tool
    def add(a: int, b: int) -> int:
        """Add numbers."""
        return a + b

    adapter = MCPAdapter(server.registry)

    # Test list_tools mapping
    # Retrieve using a dummy context
    class DummyContext:
        pass

    ctx = DummyContext()
    # Call handle_list_tools synchronously/asynchronously
    list_result = anyio.run(adapter.handle_list_tools, ctx, None)
    assert len(list_result.tools) == 1
    mcp_tool = list_result.tools[0]
    assert mcp_tool.name == "add"
    assert mcp_tool.description == "Add numbers."
    assert mcp_tool.input_schema["properties"]["a"] == {"type": "integer"}


@pytest.mark.anyio
async def test_mcp_adapter_unknown_tool() -> None:
    """Verify that calling an unknown tool raises a standard MCP JSON-RPC error."""
    server = MCPServer("test-unknown")
    adapter = MCPAdapter(server.registry)

    class DummyContext:
        pass

    ctx = DummyContext()
    call_params = t.CallToolRequestParams(name="unknown_tool", arguments={})

    with pytest.raises(MCPError) as exc_info:
        await adapter.handle_call_tool(ctx, call_params)

    assert exc_info.value.error.code == -32601
    assert "not registered" in exc_info.value.error.message


@pytest.mark.anyio
async def test_mcp_adapter_execution_error() -> None:
    """Verify that a division by zero returns is_error=True rather than crashing."""
    server = MCPServer("test-exec-error")

    @server.tool
    def divide(a: int, b: int) -> float:
        return a / b

    adapter = MCPAdapter(server.registry)

    class DummyContext:
        pass

    ctx = DummyContext()
    call_params = t.CallToolRequestParams(name="divide", arguments={"a": 10, "b": 0})

    result = await adapter.handle_call_tool(ctx, call_params)
    assert result.is_error is True
    assert "division by zero" in result.content[0].text

