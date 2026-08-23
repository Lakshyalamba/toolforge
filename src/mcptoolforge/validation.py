import enum
import inspect
import types
import typing
from typing import Any

from mcptoolforge.errors import ToolValidationError


def _validate_type(val: Any, ann: Any, param_name: str, tool_name: str) -> Any:
    """Validate and normalize a value against a type annotation."""
    if ann is inspect.Parameter.empty or ann is Any:
        return val

    # None / NoneType
    if ann is None or ann is type(None):
        if val is None:
            return None
        raise ToolValidationError(
            f"Tool '{tool_name}': parameter '{param_name}' expected None, "
            f"received {type(val).__name__}."
        )

    # Union Types / Optional
    origin = getattr(ann, "__origin__", None)
    if origin is typing.Union or (hasattr(types, "UnionType") and isinstance(ann, types.UnionType)):
        args = typing.get_args(ann)
        # Try to validate against each union type option
        for arg in args:
            try:
                return _validate_type(val, arg, param_name, tool_name)
            except ToolValidationError:
                continue

        # If all options failed, build a clean error message
        expected_types = " | ".join(
            getattr(arg, "__name__", str(arg)) for arg in args if arg is not type(None)
        )
        if type(None) in args:
            expected_types += " | None"
        raise ToolValidationError(
            f"Tool '{tool_name}': parameter '{param_name}' expected {expected_types}, "
            f"received {type(val).__name__}."
        )

    # Lists (list, List)
    if ann is list or origin is list or origin is list:
        if not isinstance(val, list):
            raise ToolValidationError(
                f"Tool '{tool_name}': parameter '{param_name}' expected list, "
                f"received {type(val).__name__}."
            )
        args = typing.get_args(ann)
        if not args:
            return val
        item_type = args[0]
        validated_list = []
        for i, item in enumerate(val):
            try:
                validated_list.append(
                    _validate_type(item, item_type, f"{param_name}[{i}]", tool_name)
                )
            except ToolValidationError as e:
                raise ToolValidationError(
                    f"Tool '{tool_name}': parameter '{param_name}' "
                    f"element at index {i} invalid: {e}"
                ) from e
        return validated_list

    # Dictionaries (dict, Dict)
    if ann is dict or origin is dict or origin is dict:
        if not isinstance(val, dict):
            raise ToolValidationError(
                f"Tool '{tool_name}': parameter '{param_name}' expected dict, "
                f"received {type(val).__name__}."
            )
        args = typing.get_args(ann)
        if not args:
            return val
        key_type, val_type = args[0], args[1]
        validated_dict = {}
        for k, v in val.items():
            try:
                validated_k = _validate_type(k, key_type, f"{param_name}.key", tool_name)
            except ToolValidationError as e:
                raise ToolValidationError(
                    f"Tool '{tool_name}': parameter '{param_name}' "
                    f"dictionary key '{k}' invalid: {e}"
                ) from e
            try:
                validated_v = _validate_type(v, val_type, f"{param_name}['{k}']", tool_name)
            except ToolValidationError as e:
                raise ToolValidationError(
                    f"Tool '{tool_name}': parameter '{param_name}' "
                    f"dictionary value for key '{k}' invalid: {e}"
                ) from e
            validated_dict[validated_k] = validated_v
        return validated_dict

    # Enums
    if isinstance(ann, type) and issubclass(ann, enum.Enum):
        if isinstance(val, ann):
            return val
        try:
            return ann(val)
        except ValueError:
            for member in ann:
                if member.name == val:
                    return member
            valid_choices = [m.value for m in ann]
            raise ToolValidationError(
                f"Tool '{tool_name}': parameter '{param_name}' expected one of {valid_choices}, "
                f"received '{val}'."
            ) from None

    # Primitive types (strictly rejecting booleans from matching integer/string/float)
    if ann is str:
        if isinstance(val, str) and not isinstance(val, bool):
            return val
        raise ToolValidationError(
            f"Tool '{tool_name}': parameter '{param_name}' expected string, "
            f"received {type(val).__name__}."
        )
    elif ann is int:
        if isinstance(val, int) and not isinstance(val, bool):
            return val
        raise ToolValidationError(
            f"Tool '{tool_name}': parameter '{param_name}' expected integer, "
            f"received {type(val).__name__}."
        )
    elif ann is float:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
        raise ToolValidationError(
            f"Tool '{tool_name}': parameter '{param_name}' expected float, "
            f"received {type(val).__name__}."
        )
    elif ann is bool:
        if isinstance(val, bool):
            return val
        raise ToolValidationError(
            f"Tool '{tool_name}': parameter '{param_name}' expected boolean, "
            f"received {type(val).__name__}."
        )

    # Fallback for unhandled type annotations
    return val


def validate_tool_arguments(tool: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize incoming arguments against a Tool's parameters."""
    validated: dict[str, Any] = {}

    # 1. Reject unexpected parameters
    for k in arguments:
        if k not in tool.parameters:
            raise ToolValidationError(f"Tool '{tool.name}': unexpected parameter '{k}'.")

    # 2. Validate expected parameters
    for name, param in tool.parameters.items():
        if name not in arguments:
            if param.required:
                raise ToolValidationError(
                    f"Tool '{tool.name}': missing required parameter '{name}'."
                )
            else:
                validated[name] = param.default
        else:
            val = arguments[name]
            validated[name] = _validate_type(val, param.annotation, name, tool.name)

    return validated


def _coerce_prompt_type(val: Any, ann: Any) -> Any:
    """Attempt to coerce string values into correct types for prompt parameters."""
    if isinstance(val, str):
        if ann is int:
            try:
                return int(val)
            except ValueError:
                pass
        elif ann is float:
            try:
                return float(val)
            except ValueError:
                pass
        elif ann is bool:
            if val.lower() == "true":
                return True
            if val.lower() == "false":
                return False

        # Support unions (e.g. Union[int, str], int | None)
        origin = getattr(ann, "__origin__", None)
        if origin is typing.Union or (
            hasattr(types, "UnionType") and isinstance(ann, types.UnionType)
        ):
            for arg in typing.get_args(ann):
                coerced = _coerce_prompt_type(val, arg)
                if coerced is not val:
                    return coerced
    return val


def validate_prompt_arguments(prompt: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize incoming arguments against a Prompt's parameters."""
    validated: dict[str, Any] = {}

    # 1. Reject unexpected parameters
    for k in arguments:
        if k not in prompt.parameters:
            raise ToolValidationError(f"Prompt '{prompt.name}': unexpected parameter '{k}'.")

    # 2. Validate expected parameters
    for name, param in prompt.parameters.items():
        if name not in arguments:
            if param.required:
                raise ToolValidationError(
                    f"Prompt '{prompt.name}': missing required parameter '{name}'."
                )
            else:
                validated[name] = param.default
        else:
            val = arguments[name]
            coerced_val = _coerce_prompt_type(val, param.annotation)
            validated[name] = _validate_type(coerced_val, param.annotation, name, prompt.name)

    return validated
