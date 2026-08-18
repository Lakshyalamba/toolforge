import inspect
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from toolforge.errors import ResourceRegistrationError


def validate_uri(uri: str) -> str:
    """Validate that the URI is a valid format and is non-empty."""
    if not isinstance(uri, str):
        raise ResourceRegistrationError("Resource URI must be a string.")
    if not uri.strip():
        raise ResourceRegistrationError("Resource URI cannot be empty or whitespace-only.")
    parsed = urlparse(uri)
    if not parsed.scheme or not (parsed.netloc or parsed.path):
        raise ResourceRegistrationError(f"Invalid resource URI format: '{uri}'")
    return uri.strip()


class Resource:
    """Represents a registered resource in ToolForge."""

    def __init__(
        self,
        uri: str,
        fn: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ):
        if not callable(fn):
            raise ResourceRegistrationError("Registered object must be a callable.")

        self._uri = validate_uri(uri)
        self._fn = fn

        # Name validation
        if name is not None:
            if not isinstance(name, str):
                raise ResourceRegistrationError("Resource name must be a string.")
            if not name.strip():
                raise ResourceRegistrationError("Resource name cannot be empty or whitespace-only.")
            self._name = name.strip()
        else:
            self._name = fn.__name__

        # Description validation
        if description is not None:
            if not isinstance(description, str):
                raise ResourceRegistrationError("Resource description must be a string.")
            if not description.strip():
                raise ResourceRegistrationError(
                    "Resource description cannot be empty or whitespace-only."
                )
            self._description = description.strip()
        else:
            doc = inspect.getdoc(fn)
            self._description = doc.strip() if doc else "No description provided."

        # MIME type validation
        if mime_type is not None:
            if not isinstance(mime_type, str):
                raise ResourceRegistrationError("Resource MIME type must be a string.")
            if not mime_type.strip():
                raise ResourceRegistrationError(
                    "Resource MIME type cannot be empty or whitespace-only."
                )
            self._mime_type = mime_type.strip()
        else:
            self._mime_type = None

    @property
    def uri(self) -> str:
        return self._uri

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
    def mime_type(self) -> str | None:
        return self._mime_type

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._fn(*args, **kwargs)

    def __repr__(self) -> str:
        return f"Resource(uri={self.uri!r}, name={self.name!r}, mime_type={self.mime_type!r})"
