import inspect
import re
from collections.abc import Callable
from typing import Any, get_type_hints

from mcptoolforge.errors import ToolRegistrationError


class PromptParameter:
    """Represents an argument/parameter of a prompt."""

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
            f"PromptParameter(name={self.name!r}, annotation={self.annotation!r}, "
            f"default={self.default!r}, required={self.required!r})"
        )


class Prompt:
    """Represents a registered prompt template in MCPToolForge."""

    def __init__(
        self,
        fn: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ):
        if not callable(fn):
            raise ToolRegistrationError("Registered prompt object must be a callable.")

        self._fn = fn

        # Name validation
        if name is not None:
            if not isinstance(name, str):
                raise ToolRegistrationError("Prompt name must be a string.")
            if not name.strip():
                raise ToolRegistrationError("Prompt name cannot be empty or whitespace-only.")
            self._name = name.strip()
        else:
            self._name = fn.__name__

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", self._name):
            raise ToolRegistrationError(
                f"Invalid prompt name: '{self._name}'. "
                "Must be alphanumeric, underscores, or hyphens."
            )

        # Description validation
        if description is not None:
            if not isinstance(description, str):
                raise ToolRegistrationError("Prompt description must be a string.")
            if not description.strip():
                raise ToolRegistrationError(
                    "Prompt description cannot be empty or whitespace-only."
                )
            self._description = description.strip()
        else:
            doc = inspect.getdoc(fn)
            self._description = doc.strip() if doc else "No description provided."

        # Introspect function parameters
        self._parameters: dict[str, PromptParameter] = {}
        try:
            sig = inspect.signature(fn)
            try:
                type_hints = get_type_hints(fn)
            except (TypeError, NameError):
                type_hints = {}
        except Exception as e:
            raise ToolRegistrationError(f"Failed to inspect prompt function signature: {e}") from e

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            annotation = type_hints.get(param_name, param.annotation)
            required = param.default is inspect.Parameter.empty
            default = inspect.Parameter.empty if required else param.default

            self._parameters[param_name] = PromptParameter(
                name=param_name,
                annotation=annotation,
                default=default,
                required=required,
                kind=param.kind,
            )

        self._return_type = type_hints.get("return", sig.return_annotation)

    @property
    def fn(self) -> Callable[..., Any]:
        return self._fn

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, PromptParameter]:
        return self._parameters

    @property
    def return_type(self) -> Any:
        return self._return_type

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._fn(*args, **kwargs)

    def __repr__(self) -> str:
        return f"Prompt(name={self.name!r}, description={self.description!r})"
