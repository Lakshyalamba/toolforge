import inspect
import re
from collections.abc import Callable
from typing import Any, get_type_hints

from toolforge.errors import (
    ToolAlreadyRegisteredError,
    ToolNotFoundError,
    ToolRegistrationError,
)


class ToolParameter:
    """Represents an input parameter of a tool."""

    def __init__(
        self,
        name: str,
        annotation: Any,
        default: Any,
        required: bool,
        kind: inspect._ParameterKind,
    ):
        self.name = name
        self.annotation = annotation
        self.default = default
        self.required = required
        self.kind = kind

    def __repr__(self) -> str:
        return (
            f"ToolParameter(name={self.name!r}, annotation={self.annotation!r}, "
            f"default={self.default!r}, required={self.required!r}, kind={self.kind!r})"
        )


class Tool:
    """Represents a registered tool in ToolForge."""

    def __init__(
        self,
        fn: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ):
        if not callable(fn):
            raise ToolRegistrationError("Registered object must be a callable.")

        self.fn = fn
        self.name = name or fn.__name__
        self.description = description or inspect.getdoc(fn) or ""

        # Validate name format (standard identifier conventions)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", self.name):
            raise ToolRegistrationError(
                f"Invalid tool name: '{self.name}'. Must be alphanumeric, underscores, or hyphens."
            )

        # Introspect function parameters and return type
        self.parameters: dict[str, ToolParameter] = {}
        try:
            sig = inspect.signature(fn)
            try:
                type_hints = get_type_hints(fn)
            except (TypeError, NameError):
                # Fallback if types cannot be resolved (e.g. forward refs not in scope)
                type_hints = {}
        except Exception as e:
            raise ToolRegistrationError(f"Failed to inspect function signature: {e}") from e

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            annotation = type_hints.get(param_name, param.annotation)
            required = param.default is inspect.Parameter.empty
            default = inspect.Parameter.empty if required else param.default

            self.parameters[param_name] = ToolParameter(
                name=param_name,
                annotation=annotation,
                default=default,
                required=required,
                kind=param.kind,
            )

        self.return_type = type_hints.get("return", sig.return_annotation)

    @property
    def input_schema(self) -> dict[str, Any]:
        """Generate the input JSON Schema for this tool's parameters."""
        from toolforge.schema import generate_input_schema
        return generate_input_schema(self.parameters, self.name)

    @property
    def schema(self) -> dict[str, Any]:
        """Lazy schema generation to decouple schema structure from representation."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.fn(*args, **kwargs)

    def __repr__(self) -> str:
        return f"Tool(name={self.name!r}, description={self.description!r})"


class ToolRegistry:
    """Manages tool storage, lookup, and deletion."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry."""
        if tool.name in self._tools:
            raise ToolAlreadyRegisteredError(
                f"Duplicate tool name: '{tool.name}' is already registered."
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """Retrieve a tool by name."""
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def remove(self, name: str) -> None:
        """Remove a tool by name."""
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' is not registered and cannot be removed.")
        del self._tools[name]

    def list(self) -> list[Tool]:
        """Return a list of all registered tools."""
        return list(self._tools.values())

    def contains(self, name: str) -> bool:
        """Check if a tool is registered by name."""
        return name in self._tools
