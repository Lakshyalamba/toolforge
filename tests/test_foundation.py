import inspect

import pytest

from mcptoolforge import (
    MCPServer,
    ToolAlreadyRegisteredError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistrationError,
    ToolValidationError,
)
from mcptoolforge.execution import execute_tool
from mcptoolforge.registry import Tool, ToolRegistry


def test_mcpserver_initialization() -> None:
    server = MCPServer("test-server")
    assert server.name == "test-server"
    assert len(server.tools) == 0


def test_tool_decorator_direct() -> None:
    server = MCPServer("test-server")

    @server.tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    tools = server.tools
    assert len(tools) == 1
    assert tools[0].name == "add"
    assert tools[0].description == "Add two numbers."
    assert tools[0](2, 3) == 5


def test_tool_decorator_args() -> None:
    server = MCPServer("test-server")

    @server.tool(name="custom_multiply", description="Multiply parameters.")
    def multiply(x: float, y: float) -> float:
        return x * y

    tool_obj = server.get_tool("custom_multiply")
    assert tool_obj.name == "custom_multiply"
    assert tool_obj.description == "Multiply parameters."
    assert tool_obj(2.5, 4.0) == 10.0


def test_duplicate_and_invalid_tool_names() -> None:
    server = MCPServer("test-server")

    @server.tool
    def my_tool() -> str:
        return "ok"

    # Duplicate name should raise ToolAlreadyRegisteredError
    with pytest.raises(ToolAlreadyRegisteredError) as exc_info:

        @server.tool(name="my_tool")
        def another_tool() -> str:
            return "duplicate"

    assert "Duplicate tool name" in str(exc_info.value)

    # Invalid characters in name should raise ToolRegistrationError
    with pytest.raises(ToolRegistrationError) as exc_info:

        @server.tool(name="invalid name with spaces")
        def bad_name_tool() -> str:
            return "bad"

    assert "Invalid tool name" in str(exc_info.value)


def test_schema_generation() -> None:
    server = MCPServer("test-server")

    @server.tool
    def check_types(
        a: int,
        b: str,
        c: float,
        d: bool,
        e: list,
        f: dict,
        g,  # untyped
        h: int = 10,  # default
    ) -> None:
        pass

    tool_obj = server.get_tool("check_types")
    schema = tool_obj.schema

    assert schema["name"] == "check_types"
    assert "inputSchema" in schema
    input_schema = schema["inputSchema"]
    assert input_schema["type"] == "object"

    props = input_schema["properties"]
    assert props["a"]["type"] == "integer"
    assert props["b"]["type"] == "string"
    assert props["c"]["type"] == "number"
    assert props["d"]["type"] == "boolean"
    assert props["e"]["type"] == "array"
    assert props["f"]["type"] == "object"
    assert props["g"] == {}  # unconstrained fallback
    assert props["h"]["type"] == "integer"

    # h has default, so it shouldn't be in the required list
    required = input_schema["required"]
    assert "a" in required
    assert "g" in required
    assert "h" not in required


@pytest.mark.anyio
async def test_tool_execution_sync() -> None:
    server = MCPServer("test-server")

    @server.tool
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    tool_obj = server.get_tool("greet")

    # Successful run
    res = await execute_tool(tool_obj, {"name": "Alice"})
    assert res == "Hello, Alice!"

    # Missing argument
    with pytest.raises(ToolValidationError) as exc_info:
        await execute_tool(tool_obj, {})
    assert "missing required parameter 'name'" in str(exc_info.value)

    # Exception inside tool function
    @server.tool
    def divide(x: int, y: int) -> float:
        return x / y

    div_tool = server.get_tool("divide")
    with pytest.raises(ToolExecutionError) as exc_info:
        await execute_tool(div_tool, {"x": 10, "y": 0})
    assert "Error executing tool" in str(exc_info.value)


@pytest.mark.anyio
async def test_tool_execution_async() -> None:
    server = MCPServer("test-server")

    @server.tool
    async def fetch_data(key: str) -> dict:
        return {"key": key, "status": "loaded"}

    tool_obj = server.get_tool("fetch_data")
    res = await execute_tool(tool_obj, {"key": "user_123"})
    assert res == {"key": "user_123", "status": "loaded"}


# --- NEW COMPREHENSIVE TESTS ---


def test_registry_independent_usage() -> None:
    """Test ToolRegistry works independently without MCPServer."""
    registry = ToolRegistry()

    def foo(x: int) -> int:
        """Foo function."""
        return x

    tool = Tool(foo)
    registry.register(tool)

    assert registry.contains("foo")
    assert registry.get("foo") is tool
    assert len(registry.list()) == 1

    registry.remove("foo")
    assert not registry.contains("foo")
    assert len(registry.list()) == 0


def test_tool_docstring_fallback() -> None:
    """Verify sensible fallback if docstring is missing."""
    server = MCPServer("test-server")

    @server.tool
    def no_doc(x: int) -> int:
        return x

    tool_obj = server.get_tool("no_doc")
    assert tool_obj.description == "No description provided."


def test_parameter_introspection_details() -> None:
    """Test detailed parameter metadata capture."""
    server = MCPServer("test-server")

    @server.tool
    def complex_params(
        a: int,
        b: str = "default_b",
        *args,
        c: float = 1.0,
        **kwargs,
    ) -> None:
        pass

    tool_obj = server.get_tool("complex_params")

    assert "a" in tool_obj.parameters
    param_a = tool_obj.parameters["a"]
    assert param_a.name == "a"
    assert param_a.annotation is int
    assert param_a.default is inspect.Parameter.empty
    assert param_a.required is True
    assert param_a.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

    assert "b" in tool_obj.parameters
    param_b = tool_obj.parameters["b"]
    assert param_b.name == "b"
    assert param_b.annotation is str
    assert param_b.default == "default_b"
    assert param_b.required is False
    assert param_b.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

    assert "c" in tool_obj.parameters
    param_c = tool_obj.parameters["c"]
    assert param_c.name == "c"
    assert param_c.annotation is float
    assert param_c.default == 1.0
    assert param_c.required is False
    assert param_c.kind == inspect.Parameter.KEYWORD_ONLY


def test_mcpserver_run_setup() -> None:
    """Test MCPServer runner can be set up correctly."""
    server = MCPServer("test")
    from mcptoolforge.mcp.server import MCPServerRunner

    runner = MCPServerRunner(server.name, server.registry)
    assert runner.server_name == "test"


def test_lookup_missing_tool_raises_not_found() -> None:
    """Verify that looking up a missing tool raises ToolNotFoundError."""
    server = MCPServer("test")
    with pytest.raises(ToolNotFoundError) as exc_info:
        server.get_tool("unknown_tool")
    assert "Tool 'unknown_tool' is not registered" in str(exc_info.value)


def test_duplicate_registration_on_registry() -> None:
    """Verify duplicate registrations raise ToolAlreadyRegisteredError."""
    registry = ToolRegistry()

    def dummy() -> None:
        pass

    tool_1 = Tool(dummy, name="dummy")
    tool_2 = Tool(dummy, name="dummy")

    registry.register(tool_1)
    with pytest.raises(ToolAlreadyRegisteredError) as exc_info:
        registry.register(tool_2)
    assert "is already registered" in str(exc_info.value)


def test_tool_registry_remove_missing_raises_not_found() -> None:
    """Verify removing a missing tool from registry raises ToolNotFoundError."""
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.remove("non_existent")
