import logging
import unittest.mock as mock

import mcp.types as t
import pytest

from toolforge import (
    MCPServer,
    logging_middleware,
    sync_logging_middleware,
    sync_timing_middleware,
    timing_middleware,
)
from toolforge.mcp.adapter import MCPAdapter
from toolforge.mcp.server import MCPServerRunner


class DummyContext:
    pass


@pytest.mark.anyio
async def test_middleware_registration_and_order() -> None:
    """Verify middleware executes in correct nested order:
    A_before -> B_before -> Tool -> B_after -> A_after.
    """
    server = MCPServer("test")
    order = []

    @server.middleware
    async def middleware_a(context, next_callable):
        order.append("a_before")
        res = await next_callable()
        order.append("a_after")
        return res

    @server.middleware
    async def middleware_b(context, next_callable):
        order.append("b_before")
        res = await next_callable()
        order.append("b_after")
        return res

    @server.tool
    def add(a: int) -> int:
        order.append("tool")
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})
    res = await adapter.handle_call_tool(DummyContext(), params)

    assert res.is_error is False
    assert res.content[0].text == "10"
    assert order == ["a_before", "b_before", "tool", "b_after", "a_after"]


@pytest.mark.anyio
async def test_middleware_context_fields() -> None:
    """Verify MiddlewareContext contains correct execution metadata."""
    server = MCPServer("test")
    context_captured = {}

    @server.middleware
    async def capture_middleware(context, next_callable):
        context_captured["tool_name"] = context.tool_name
        context_captured["arguments"] = context.arguments
        context_captured["server"] = context.server
        return await next_callable()

    @server.tool
    def add(a: int) -> int:
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})
    await adapter.handle_call_tool(DummyContext(), params)

    assert context_captured["tool_name"] == "add"
    assert context_captured["arguments"] == {"a": 10}
    assert context_captured["server"] == server


@pytest.mark.anyio
async def test_sync_middleware_sync_tool() -> None:
    """Verify synchronous middleware executes correctly with synchronous tool."""
    server = MCPServer("test")
    order = []

    @server.middleware
    def sync_mw(context, next_callable):
        order.append("mw_before")
        res = next_callable()
        order.append("mw_after")
        return res

    @server.tool
    def add(a: int) -> int:
        order.append("tool")
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})
    res = await adapter.handle_call_tool(DummyContext(), params)

    assert res.is_error is False
    assert order == ["mw_before", "tool", "mw_after"]


@pytest.mark.anyio
async def test_async_middleware_sync_tool() -> None:
    """Verify asynchronous middleware wraps synchronous tool correctly."""
    server = MCPServer("test")
    order = []

    @server.middleware
    async def async_mw(context, next_callable):
        order.append("mw_before")
        res = await next_callable()
        order.append("mw_after")
        return res

    @server.tool
    def add(a: int) -> int:
        order.append("tool")
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})
    res = await adapter.handle_call_tool(DummyContext(), params)

    assert res.is_error is False
    assert order == ["mw_before", "tool", "mw_after"]


@pytest.mark.anyio
async def test_sync_middleware_async_tool_raises_error() -> None:
    """Verify synchronous middleware preceding async tool raises a configuration error."""
    server = MCPServer("test")

    @server.middleware
    def sync_mw(context, next_callable):
        return next_callable()

    @server.tool
    async def add(a: int) -> int:
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})

    res = await adapter.handle_call_tool(DummyContext(), params)
    assert res.is_error is True
    assert "Synchronous middleware" in res.content[0].text


@pytest.mark.anyio
async def test_middleware_error_observation() -> None:
    """Verify middlewares can observe and propagate exceptions safely."""
    server = MCPServer("test")
    errors_observed = []

    @server.middleware
    async def error_mw(context, next_callable):
        try:
            return await next_callable()
        except Exception as e:
            errors_observed.append(e)
            raise

    @server.tool
    def divide(a: int) -> float:
        return a / 0

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="divide", arguments={"a": 10})
    res = await adapter.handle_call_tool(DummyContext(), params)

    assert res.is_error is True
    assert len(errors_observed) == 1
    assert "division by zero" in str(errors_observed[0])


@pytest.mark.anyio
async def test_middleware_logic_failure() -> None:
    """Verify that exceptions raised inside the middleware logic itself map to MiddlewareError."""
    server = MCPServer("test")

    @server.middleware
    async def failing_mw(context, next_callable):
        raise ValueError("Middleware logic failed!")

    @server.tool
    def add(a: int) -> int:
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})
    res = await adapter.handle_call_tool(DummyContext(), params)

    assert res.is_error is True
    assert "Middleware failed during execution" in res.content[0].text
    assert "Middleware logic failed" in res.content[0].text


@pytest.mark.anyio
async def test_built_in_timing_middlewares(caplog) -> None:
    """Verify built-in timing middlewares execute and log duration measurements to stderr."""
    server = MCPServer("test")
    server.add_middleware(timing_middleware)
    server.add_middleware(sync_timing_middleware)

    @server.tool
    def add(a: int) -> int:
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})
    with caplog.at_level(logging.INFO):
        res = await adapter.handle_call_tool(DummyContext(), params)

    assert res.is_error is False
    records = [r.message for r in caplog.records]
    assert any("execution took" in msg for msg in records)


@pytest.mark.anyio
async def test_built_in_logging_middlewares(caplog) -> None:
    """Verify built-in logging middlewares trace calls to stderr."""
    server = MCPServer("test")
    server.add_middleware(logging_middleware)
    server.add_middleware(sync_logging_middleware)

    @server.tool
    def add(a: int) -> int:
        return a

    adapter = MCPAdapter(server.registry, server=server)
    params = t.CallToolRequestParams(name="add", arguments={"a": 10})
    with caplog.at_level(logging.INFO):
        res = await adapter.handle_call_tool(DummyContext(), params)

    assert res.is_error is False
    records = [r.message for r in caplog.records]
    assert any("Calling tool 'add'" in msg for msg in records)
    assert any("Completed tool 'add' successfully" in msg for msg in records)


@pytest.mark.anyio
async def test_lifecycle_hooks() -> None:
    """Verify sync/async startup/shutdown hooks execute at appropriate server lifecycle phases."""
    server = MCPServer("test")
    events = []

    @server.on_startup
    def sync_startup():
        events.append("sync_startup")

    @server.on_startup
    async def async_startup():
        events.append("async_startup")

    @server.on_shutdown
    def sync_shutdown():
        events.append("sync_shutdown")

    @server.on_shutdown
    async def async_shutdown():
        events.append("async_shutdown")

    runner = MCPServerRunner("test-run", server.registry, server=server)

    with (
        mock.patch("mcp.server.lowlevel.Server.run", new_callable=mock.AsyncMock),
        mock.patch("toolforge.mcp.server.stdio_server", new_callable=mock.MagicMock) as mock_stdio,
    ):
        mock_stdio.return_value.__aenter__.return_value = ("read", "write")
        await runner.run_async()

    assert "sync_startup" in events
    assert "async_startup" in events
    assert "sync_shutdown" in events
    assert "async_shutdown" in events
