import enum
import json
from typing import Any

import pytest

from toolforge import MCPServer, SchemaGenerationError


def test_schema_primitive_types() -> None:
    """Test primitive type mappings: str, int, float, bool."""
    server = MCPServer("test-server")

    @server.tool
    def test_tool(
        a: str,
        b: int,
        c: float,
        d: bool,
    ) -> None:
        pass

    tool = server.get_tool("test_tool")
    schema = tool.input_schema

    assert schema["type"] == "object"
    assert schema["properties"]["a"] == {"type": "string"}
    assert schema["properties"]["b"] == {"type": "integer"}
    assert schema["properties"]["c"] == {"type": "number"}
    assert schema["properties"]["d"] == {"type": "boolean"}
    # All are required since no defaults exist
    assert set(schema["required"]) == {"a", "b", "c", "d"}


def test_schema_defaults_and_required() -> None:
    """Verify default values are captured and exclude parameters from required list."""
    server = MCPServer("test-server")

    @server.tool
    def greet(
        name: str,
        greeting: str = "Hello",
        count: int = 1,
        flag: bool = True,
        ratio: float = 0.5,
        nothing: str | None = None,
    ) -> None:
        pass

    tool = server.get_tool("greet")
    schema = tool.input_schema

    # Only 'name' has no default and is required
    assert schema["required"] == ["name"]
    assert schema["properties"]["name"] == {"type": "string"}
    assert schema["properties"]["greeting"] == {"type": "string", "default": "Hello"}
    assert schema["properties"]["count"] == {"type": "integer", "default": 1}
    assert schema["properties"]["flag"] == {"type": "boolean", "default": True}
    assert schema["properties"]["ratio"] == {"type": "number", "default": 0.5}
    assert schema["properties"]["nothing"] == {"type": ["string", "null"], "default": None}


def test_schema_list_types() -> None:
    """Test list types list[str], list[int], List[str]."""
    server = MCPServer("test-server")

    @server.tool
    def process_lists(
        tags: list[str],
        numbers: list[int],
        legacy_tags: list[str],
    ) -> None:
        pass

    tool = server.get_tool("process_lists")
    schema = tool.input_schema

    assert schema["properties"]["tags"] == {"type": "array", "items": {"type": "string"}}
    assert schema["properties"]["numbers"] == {"type": "array", "items": {"type": "integer"}}
    assert schema["properties"]["legacy_tags"] == {"type": "array", "items": {"type": "string"}}


def test_schema_dict_types() -> None:
    """Test dict types dict[str, str] and dict[str, int]."""
    server = MCPServer("test-server")

    @server.tool
    def process_dicts(
        metadata: dict[str, str],
        counts: dict[str, int],
    ) -> None:
        pass

    tool = server.get_tool("process_dicts")
    schema = tool.input_schema

    assert schema["properties"]["metadata"] == {
        "type": "object",
        "additionalProperties": {"type": "string"},
    }
    assert schema["properties"]["counts"] == {
        "type": "object",
        "additionalProperties": {"type": "integer"},
    }


def test_schema_optional_and_unions() -> None:
    """Test modern optional union typing and classical Optional[T]."""
    server = MCPServer("test-server")

    @server.tool
    def process_optionals(
        a: str | None,
        b: str | None,
        c: int | float | None,
    ) -> None:
        pass

    tool = server.get_tool("process_optionals")
    schema = tool.input_schema

    assert schema["properties"]["a"] == {"type": ["string", "null"]}
    assert schema["properties"]["b"] == {"type": ["string", "null"]}
    # Complex union containing multiple types
    assert schema["properties"]["c"] == {
        "anyOf": [{"type": "integer"}, {"type": "number"}, {"type": "null"}]
    }


def test_schema_enum_types() -> None:
    """Test Python Enum parameter types."""
    server = MCPServer("test-server")

    class Colors(enum.StrEnum):
        RED = "red"
        BLUE = "blue"

    class Numbers(int, enum.Enum):
        ONE = 1
        TWO = 2

    @server.tool
    def choose_enum(
        color: Colors,
        num: Numbers,
    ) -> None:
        pass

    tool = server.get_tool("choose_enum")
    schema = tool.input_schema

    assert schema["properties"]["color"] == {"type": "string", "enum": ["red", "blue"]}
    assert schema["properties"]["num"] == {"type": "integer", "enum": [1, 2]}


def test_schema_any_and_missing() -> None:
    """Verify Any type and missing annotations map to unconstrained schema {}."""
    server = MCPServer("test-server")

    @server.tool
    def unconstrained(
        a: Any,
        b,
    ) -> None:
        pass

    tool = server.get_tool("unconstrained")
    schema = tool.input_schema

    assert schema["properties"]["a"] == {}
    assert schema["properties"]["b"] == {}


def test_schema_json_serialization() -> None:
    """Verify the generated schema can be fully serialized with json.dumps."""
    server = MCPServer("test-server")

    @server.tool
    def serialize_me(
        q: str,
        limit: int = 10,
        tags: list[str] | None = None,
    ) -> None:
        pass

    tool = server.get_tool("serialize_me")
    schema = tool.input_schema

    json_str = json.dumps(schema)
    assert json_str is not None
    loaded = json.loads(json_str)
    assert loaded["type"] == "object"
    assert loaded["properties"]["q"]["type"] == "string"


def test_schema_unsupported_type_error() -> None:
    """Verify that unsupported types raise a detailed SchemaGenerationError."""
    server = MCPServer("test-server")

    class UnserializableObject:
        pass

    # Custom unserializable parameter should raise error on .input_schema lookup
    @server.tool
    def bad_tool(obj: UnserializableObject) -> None:
        pass

    tool = server.get_tool("bad_tool")
    with pytest.raises(SchemaGenerationError) as exc_info:
        _ = tool.input_schema

    err_msg = str(exc_info.value)
    assert "Unsupported type" in err_msg
    assert "bad_tool" in err_msg
    assert "obj" in err_msg


def test_schema_unsupported_dict_key_error() -> None:
    """Verify that non-string dict keys raise a SchemaGenerationError."""
    server = MCPServer("test-server")

    @server.tool
    def bad_dict_tool(mapping: dict[int, str]) -> None:
        pass

    tool = server.get_tool("bad_dict_tool")
    with pytest.raises(SchemaGenerationError) as exc_info:
        _ = tool.input_schema

    err_msg = str(exc_info.value)
    assert "Dictionary keys must be 'str'" in err_msg
    assert "mapping" in err_msg
    assert "bad_dict_tool" in err_msg


def test_schema_multiple_tools_isolation() -> None:
    """Verify multiple tools have independent schemas."""
    server = MCPServer("test-server")

    @server.tool
    def tool_one(x: int) -> None:
        pass

    @server.tool
    def tool_two(y: str) -> None:
        pass

    t1 = server.get_tool("tool_one")
    t2 = server.get_tool("tool_two")

    assert "x" in t1.input_schema["properties"]
    assert "y" not in t1.input_schema["properties"]
    assert "y" in t2.input_schema["properties"]
    assert "x" not in t2.input_schema["properties"]
