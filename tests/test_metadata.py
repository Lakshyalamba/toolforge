import mcp.types as t
import pytest

from toolforge import (
    MCPServer,
    ToolAlreadyRegisteredError,
    ToolNotFoundError,
    ToolRegistrationError,
)
from toolforge.mcp.adapter import MCPAdapter


def test_simple_decorator() -> None:
    """Verify simple @server.tool decoration behavior."""
    server = MCPServer("test")

    @server.tool
    def add(a: int, b: int) -> int:
        """Add numbers."""
        return a + b

    tool = server.get_tool("add")
    assert tool.name == "add"
    assert tool.description == "Add numbers."
    assert tool.tags == []
    assert tool.metadata == {}
    assert add(2, 3) == 5  # Remains callable


def test_configured_decorator() -> None:
    """Verify parameterized @server.tool(...) decoration metadata assignments."""
    server = MCPServer("test")

    @server.tool(
        name="calc",
        description="A calculator tool",
        tags=["math", "simple"],
        metadata={"category": "arithmetic"},
    )
    def add(a: int, b: int) -> int:
        """Add numbers."""
        return a + b

    tool = server.get_tool("calc")
    assert tool.name == "calc"
    assert tool.description == "A calculator tool"
    assert tool.tags == ["math", "simple"]
    assert tool.metadata == {"category": "arithmetic"}
    assert add(2, 3) == 5
    with pytest.raises(ToolNotFoundError):
        server.get_tool("add")


def test_configured_empty_parentheses() -> None:
    """Verify decoration with empty parentheses @server.tool() defaults correctly."""
    server = MCPServer("test")

    @server.tool()
    def greet(name: str) -> str:
        """Say hello."""
        return f"Hello {name}"

    tool = server.get_tool("greet")
    assert tool.name == "greet"
    assert tool.description == "Say hello."
    assert tool.tags == []
    assert tool.metadata == {}


def test_custom_name_validation() -> None:
    """Verify name validations for custom names."""
    server = MCPServer("test")

    # Empty name
    with pytest.raises(ToolRegistrationError):

        @server.tool(name="")
        def add1(a: int) -> int:
            return a

    # Whitespace-only name
    with pytest.raises(ToolRegistrationError):

        @server.tool(name="   ")
        def add2(a: int) -> int:
            return a

    # Invalid characters
    with pytest.raises(ToolRegistrationError):

        @server.tool(name="invalid name spaces")
        def add3(a: int) -> int:
            return a

    # Non-string name
    with pytest.raises(ToolRegistrationError):

        @server.tool(name=123)
        def add4(a: int) -> int:
            return a


def test_duplicate_custom_names() -> None:
    """Verify registration raises error on custom name collisions."""
    server = MCPServer("test")

    @server.tool(name="duplicate_tool")
    def func1(a: int) -> int:
        return a

    with pytest.raises(ToolAlreadyRegisteredError):

        @server.tool(name="duplicate_tool")
        def func2(a: int) -> int:
            return a


def test_custom_description_override() -> None:
    """Verify custom description overrides docstrings."""
    server = MCPServer("test")

    @server.tool(description="Overridden description")
    def add(a: int, b: int) -> int:
        """Docstring description."""
        return a + b

    tool = server.get_tool("add")
    assert tool.description == "Overridden description"


def test_docstring_fallback_behavior() -> None:
    """Verify fallbacks when docstrings or descriptions are empty or missing."""
    server = MCPServer("test")

    # No docstring, no description
    @server.tool
    def add(a: int) -> int:
        return a

    tool = server.get_tool("add")
    assert tool.description == "No description provided."

    # Empty description string raises error
    with pytest.raises(ToolRegistrationError):

        @server.tool(description="")
        def add2(a: int) -> int:
            return a


def test_tags_handling_and_deduplication() -> None:
    """Verify tags normalization, deduplication, and type validation checks."""
    server = MCPServer("test")

    # Deduplication and stripping
    @server.tool(tags=["  math ", "math", "utility"])
    def add(a: int) -> int:
        return a

    tool = server.get_tool("add")
    assert tool.tags == ["math", "utility"]

    # Invalid tag lists
    with pytest.raises(ToolRegistrationError):

        @server.tool(tags="not-a-list")
        def add2(a: int) -> int:
            return a

    with pytest.raises(ToolRegistrationError):

        @server.tool(tags=["valid", 123])
        def add3(a: int) -> int:
            return a

    with pytest.raises(ToolRegistrationError):

        @server.tool(tags=["valid", ""])
        def add4(a: int) -> int:
            return a


def test_metadata_handling() -> None:
    """Verify generic metadata JSON-serializability, key conflicts, and types."""
    server = MCPServer("test")

    # Invalid metadata type
    with pytest.raises(ToolRegistrationError):

        @server.tool(metadata="not-a-dict")
        def add1(a: int) -> int:
            return a

    # Conflicting core fields
    with pytest.raises(ToolRegistrationError):

        @server.tool(metadata={"name": "override-name"})
        def add2(a: int) -> int:
            return a

    # Non-serializable values
    with pytest.raises(ToolRegistrationError):

        @server.tool(metadata={"custom": object()})
        def add3(a: int) -> int:
            return a

    # Non-string keys
    with pytest.raises(ToolRegistrationError):

        @server.tool(metadata={123: "val"})
        def add4(a: int) -> int:
            return a


def test_tool_immutability() -> None:
    """Verify read-only properties prevent casual attribute mutation."""
    server = MCPServer("test")

    @server.tool
    def add(a: int) -> int:
        return a

    tool = server.get_tool("add")
    with pytest.raises(AttributeError):
        tool.name = "new_name"  # type: ignore

    with pytest.raises(AttributeError):
        tool.fn = lambda x: x  # type: ignore

    with pytest.raises(AttributeError):
        tool.description = "new description"  # type: ignore


def test_registry_has_and_list_tools() -> None:
    """Verify has_tool and list_tools helper functions."""
    server = MCPServer("test")
    assert not server.has_tool("add")

    @server.tool
    def add(a: int) -> int:
        return a

    assert server.has_tool("add")
    tools = server.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "add"


@pytest.mark.anyio
async def test_mcp_adapter_integration() -> None:
    """Verify MCP adapter integration discovery and execution calls map custom metadata fields."""
    server = MCPServer("test")

    @server.tool(name="calculator", description="Arithmetic calculations")
    def add(a: int, b: int) -> int:
        return a + b

    adapter = MCPAdapter(server.registry, server=server)

    class DummyContext:
        pass

    ctx = DummyContext()

    # Verify Discovery lists custom name and description
    list_res = await adapter.handle_list_tools(ctx, None)
    assert len(list_res.tools) == 1
    mcp_tool = list_res.tools[0]
    assert mcp_tool.name == "calculator"
    assert mcp_tool.description == "Arithmetic calculations"

    # Verify Invocation executes using custom name
    call_params = t.CallToolRequestParams(name="calculator", arguments={"a": 5, "b": 10})
    call_res = await adapter.handle_call_tool(ctx, call_params)
    assert call_res.is_error is False
    assert call_res.content[0].text == "15"
