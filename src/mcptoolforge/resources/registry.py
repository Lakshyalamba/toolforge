from mcptoolforge.errors import ResourceAlreadyRegisteredError, ResourceNotFoundError
from mcptoolforge.resources.resource import Resource


class ResourceRegistry:
    """Manages resource storage, lookup, and deletion."""

    def __init__(self) -> None:
        self._resources: dict[str, Resource] = {}

    def register(self, resource: Resource) -> None:
        """Register a resource in the registry."""
        if resource.uri in self._resources:
            raise ResourceAlreadyRegisteredError(
                f"Duplicate resource URI: '{resource.uri}' is already registered."
            )
        self._resources[resource.uri] = resource

    def get(self, uri: str) -> Resource:
        """Retrieve a resource by its URI."""
        if uri not in self._resources:
            raise ResourceNotFoundError(f"Resource with URI '{uri}' is not registered.")
        return self._resources[uri]

    def remove(self, uri: str) -> None:
        """Remove a resource by its URI."""
        if uri not in self._resources:
            raise ResourceNotFoundError(
                f"Resource with URI '{uri}' is not registered and cannot be removed."
            )
        del self._resources[uri]

    def list(self) -> list[Resource]:
        """Return a list of all registered resources."""
        return list(self._resources.values())

    def contains(self, uri: str) -> bool:
        """Check if a resource is registered by its URI."""
        return uri in self._resources
