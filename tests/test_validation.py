import enum

import pytest

from toolforge import MCPServer, ToolExecutionError, ToolValidationError
from toolforge.execution import execute_tool
from toolforge.validation import validate_tool_arguments


class DummyEnum(enum.StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"


def test_validation_primitives_success() -> None:
    """Verify standard primitive types pass validation when correct."""
    server = MCPServer("test")

    @server.tool
    def test_tool(a: str, b: int, c: float, d: bool) -> None:
        pass

    tool = server.get_tool("test_tool")

    # All valid primitives
    args = {"a": "hello", "b": 10, "c": 3.14, "d": True}
    res = validate_tool_arguments(tool, args)
    assert res["a"] == "hello"
    assert res["b"] == 10
    assert res["c"] == 3.14
    assert res["d"] is True

    # Integers can validate successfully as float
    args_float_coercion = {"a": "hello", "b": 10, "c": 4, "d": False}
    res_coerced = validate_tool_arguments(tool, args_float_coercion)
    assert res_coerced["c"] == 4.0


def test_validation_invalid_string() -> None:
    """Verify invalid string type raises ToolValidationError."""
    server = MCPServer("test")

    @server.tool
    def test_tool(a: str) -> None:
        pass

    tool = server.get_tool("test_tool")

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"a": 123})
    
    err = str(exc_info.value)
    assert "test_tool" in err
    assert "parameter 'a' expected string, received int" in err


def test_validation_invalid_integer() -> None:
    """Verify invalid integer type raises ToolValidationError."""
    server = MCPServer("test")

    @server.tool
    def test_tool(b: int) -> None:
        pass

    tool = server.get_tool("test_tool")

    # Try passing string
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"b": "10"})
    assert "parameter 'b' expected integer, received str" in str(exc_info.value)

    # Try passing boolean (should strictly reject)
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"b": True})
    assert "parameter 'b' expected integer, received bool" in str(exc_info.value)


def test_validation_invalid_float() -> None:
    """Verify invalid float type raises ToolValidationError."""
    server = MCPServer("test")

    @server.tool
    def test_tool(c: float) -> None:
        pass

    tool = server.get_tool("test_tool")

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"c": "3.14"})
    assert "parameter 'c' expected float, received str" in str(exc_info.value)


def test_validation_invalid_boolean() -> None:
    """Verify invalid boolean type raises ToolValidationError."""
    server = MCPServer("test")

    @server.tool
    def test_tool(d: bool) -> None:
        pass

    tool = server.get_tool("test_tool")

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"d": 0})
    assert "parameter 'd' expected boolean, received int" in str(exc_info.value)


def test_validation_missing_required() -> None:
    """Verify missing required parameter raises ToolValidationError."""
    server = MCPServer("test")

    @server.tool
    def test_tool(a: str, b: int) -> None:
        pass

    tool = server.get_tool("test_tool")

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"a": "hello"})
    assert "missing required parameter 'b'" in str(exc_info.value)


def test_validation_defaults() -> None:
    """Verify default values are injected when absent from input."""
    server = MCPServer("test")

    @server.tool
    def test_tool(a: str, b: int = 100) -> None:
        pass

    tool = server.get_tool("test_tool")

    res = validate_tool_arguments(tool, {"a": "hello"})
    assert res["a"] == "hello"
    assert res["b"] == 100


def test_validation_unexpected() -> None:
    """Verify unexpected arguments raise ToolValidationError."""
    server = MCPServer("test")

    @server.tool
    def test_tool(a: str) -> None:
        pass

    tool = server.get_tool("test_tool")

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"a": "hello", "extra": 42})
    assert "unexpected parameter 'extra'" in str(exc_info.value)


def test_validation_optionals_and_none() -> None:
    """Verify Optional[str] / str | None / NoneType handling."""
    server = MCPServer("test")

    @server.tool
    def test_tool(
        a: str | None,
        b: str | None,
        c: None,
    ) -> None:
        pass

    tool = server.get_tool("test_tool")

    # Valid values
    res = validate_tool_arguments(tool, {"a": None, "b": "hello", "c": None})
    assert res["a"] is None
    assert res["b"] == "hello"
    assert res["c"] is None

    # Invalid values for c
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"a": None, "b": "hello", "c": "not-none"})
    assert "parameter 'c' expected None, received str" in str(exc_info.value)


def test_validation_lists() -> None:
    """Verify list[str] and list[int] validation."""
    server = MCPServer("test")

    @server.tool
    def test_tool(tags: list[str], codes: list[int]) -> None:
        pass

    tool = server.get_tool("test_tool")

    # Valid lists
    res = validate_tool_arguments(tool, {"tags": ["a", "b"], "codes": [1, 2]})
    assert res["tags"] == ["a", "b"]
    assert res["codes"] == [1, 2]

    # Invalid list type
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"tags": "not-a-list", "codes": [1, 2]})
    assert "parameter 'tags' expected list, received str" in str(exc_info.value)

    # Invalid list element
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"tags": ["a", 123], "codes": [1, 2]})
    assert "element at index 1 invalid" in str(exc_info.value)


def test_validation_dicts() -> None:
    """Verify dict[str, str] and dict[str, int] validation."""
    server = MCPServer("test")

    @server.tool
    def test_tool(metadata: dict[str, str], scores: dict[str, int]) -> None:
        pass

    tool = server.get_tool("test_tool")

    # Valid dicts
    res = validate_tool_arguments(tool, {"metadata": {"name": "L"}, "scores": {"math": 95}})
    assert res["metadata"] == {"name": "L"}
    assert res["scores"] == {"math": 95}

    # Invalid dictionary structure
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"metadata": "not-a-dict", "scores": {}})
    assert "parameter 'metadata' expected dict, received str" in str(exc_info.value)

    # Invalid dictionary key
    @server.tool
    def bad_key_tool(bad_map: dict[int, str]) -> None:
        pass

    bad_tool = server.get_tool("bad_key_tool")
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(bad_tool, {"bad_map": {"not-an-int": "val"}})
    assert "dictionary key" in str(exc_info.value)

    # Invalid dictionary value
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"metadata": {"name": 123}, "scores": {}})
    assert "dictionary value for key 'name' invalid" in str(exc_info.value)


def test_validation_enums() -> None:
    """Verify Enum validation and automatic normalization."""
    server = MCPServer("test")

    @server.tool
    def test_tool(op: DummyEnum) -> None:
        pass

    tool = server.get_tool("test_tool")

    # Valid enum value string (coerced to Enum instance)
    res1 = validate_tool_arguments(tool, {"op": "add"})
    assert res1["op"] is DummyEnum.ADD

    # Valid Enum instance (returned as-is)
    res2 = validate_tool_arguments(tool, {"op": DummyEnum.SUBTRACT})
    assert res2["op"] is DummyEnum.SUBTRACT

    # Invalid enum value string
    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_arguments(tool, {"op": "invalid-op"})
    assert "expected one of ['add', 'subtract']" in str(exc_info.value)


@pytest.mark.anyio
async def test_tool_execution_sync_and_async() -> None:
    """Verify sync and async tool execution flows."""
    server = MCPServer("test")

    @server.tool
    def add(a: int, b: int) -> int:
        return a + b

    @server.tool
    async def fetch(url: str) -> str:
        return f"data from {url}"

    add_tool = server.get_tool("add")
    fetch_tool = server.get_tool("fetch")

    # A. Sync execution
    add_res = await execute_tool(add_tool, {"a": 2, "b": 3})
    assert add_res == 5

    # B. Async execution
    fetch_res = await execute_tool(fetch_tool, {"url": "example.com"})
    assert fetch_res == "data from example.com"


@pytest.mark.anyio
async def test_tool_execution_exception() -> None:
    """Verify that exceptions thrown inside the tool function wrap as ToolExecutionError."""
    server = MCPServer("test")

    @server.tool
    def crash_me() -> None:
        raise ValueError("simulated internal error")

    tool = server.get_tool("crash_me")

    with pytest.raises(ToolExecutionError) as exc_info:
        await execute_tool(tool, {})
    assert "simulated internal error" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ValueError)
