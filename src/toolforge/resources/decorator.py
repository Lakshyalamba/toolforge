from collections.abc import Callable
from typing import Any, TypeVar

from toolforge.resources.resource import Resource

F = TypeVar("F", bound=Callable[..., Any])


class ResourceDecorator:
    """Decorator to register functions as resources on a ResourceRegistry."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def __call__(
        self,
        uri: str,
        name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            resource = Resource(
                uri=uri,
                fn=func,
                name=name,
                description=description,
                mime_type=mime_type,
            )
            self._registry.register(resource)
            return func

        return decorator
