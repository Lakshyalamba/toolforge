import enum
import inspect
import types
import typing
from typing import Any

from toolforge.errors import SchemaGenerationError
from toolforge.registry import ToolParameter


def _map_primitive_type(py_type: Any, param_name: str, tool_name: str) -> str:
    """Map standard Python primitive types to JSON Schema types."""
    if py_type is int:
        return "integer"
    elif py_type is float:
        return "number"
    elif py_type is str:
        return "string"
    elif py_type is bool:
        return "boolean"
    else:
        raise SchemaGenerationError(
            f"Unsupported type '{py_type}' for parameter '{param_name}' in tool '{tool_name}'. "
            "Currently supported types are: str, int, float, bool, list, dict, Enum, "
            "and Union/Optional."
        )


def _map_type(ann: Any, param_name: str, tool_name: str) -> dict[str, Any]:
    """Recursively map Python type annotations to JSON Schema dictionaries."""
    if ann is inspect.Parameter.empty or ann is Any:
        return {}

    # Handle None / NoneType
    if ann is None or ann is type(None):
        return {"type": "null"}

    # Handle standard Unions and Python 3.10+ UnionTypes
    origin = getattr(ann, "__origin__", None)
    if origin is typing.Union or (
        hasattr(types, "UnionType") and isinstance(ann, types.UnionType)
    ):
        args = typing.get_args(ann)
        is_nullable = type(None) in args
        non_null_args = [arg for arg in args if arg is not type(None)]

        mapped_schemas = [_map_type(arg, param_name, tool_name) for arg in non_null_args]

        if len(mapped_schemas) == 1:
            schema = mapped_schemas[0].copy()
            if "type" in schema:
                t = schema["type"]
                if isinstance(t, list):
                    schema["type"] = [*t, "null"] if "null" not in t else t
                else:
                    schema["type"] = [t, "null"]
            else:
                schema["type"] = "null"
            return schema
        else:
            if is_nullable:
                return {"anyOf": [*mapped_schemas, {"type": "null"}]}
            else:
                return {"anyOf": mapped_schemas}

    # Handle List types (list[T], List[T])
    if ann is list or origin is list or origin is list:
        args = typing.get_args(ann)
        if not args:
            return {"type": "array"}
        item_type = args[0]
        items_schema = _map_type(item_type, param_name, tool_name)
        return {"type": "array", "items": items_schema}

    # Handle Dict types (dict[K, V], Dict[K, V])
    if ann is dict or origin is dict or origin is dict:
        args = typing.get_args(ann)
        if not args:
            return {"type": "object"}
        key_type, val_type = args[0], args[1]
        if key_type is not str:
            raise SchemaGenerationError(
                f"Dictionary keys must be 'str' type for parameter '{param_name}' "
                f"in tool '{tool_name}'."
            )
        val_schema = _map_type(val_type, param_name, tool_name)
        return {"type": "object", "additionalProperties": val_schema}

    # Handle Enum types
    if isinstance(ann, type) and issubclass(ann, enum.Enum):
        values = [m.value for m in ann]
        if not values:
            raise SchemaGenerationError(
                f"Empty enum class '{ann.__name__}' for parameter '{param_name}' "
                f"in tool '{tool_name}'."
            )
        val_types = {type(v) for v in values}
        if len(val_types) == 1:
            val_type = next(iter(val_types))
            json_type = _map_primitive_type(val_type, param_name, tool_name)
        else:
            json_type = "string"  # Fallback for mixed types
        return {"type": json_type, "enum": values}

    # Standard primitive types
    json_type = _map_primitive_type(ann, param_name, tool_name)
    return {"type": json_type}


def generate_input_schema(parameters: dict[str, ToolParameter], tool_name: str) -> dict[str, Any]:
    """Generate the input JSON Schema from introspected Tool parameters."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in parameters.items():
        param_schema = _map_type(param.annotation, param_name, tool_name)

        # Handle defaults
        if param.default is not inspect.Parameter.empty:
            param_schema["default"] = param.default
        else:
            required.append(param_name)

        properties[param_name] = param_schema

    input_schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        input_schema["required"] = required

    return input_schema


def generate_tool_schema(func: Any, name: str, description: str) -> dict[str, Any]:
    """Generate a JSON Schema representation for a tool's parameters.

    Preserves existing functionality by delegating to input schema generation.
    """
    from toolforge.registry import Tool
    tool = Tool(func, name=name, description=description)
    return {
        "name": name,
        "description": description,
        "inputSchema": generate_input_schema(tool.parameters, name),
    }
