import pytest

from mcptoolforge import (
    MCPServer,
    ResourceAlreadyRegisteredError,
    ResourceNotFoundError,
    ResourceRegistrationError,
)
from mcptoolforge.resources import Resource, ResourceRegistry


def test_resource_registration_and_lookup() -> None:
    """Verify registry storage and registration validations."""
    registry = ResourceRegistry()

    def dummy():
        return "data"

    res = Resource(
        "config://app",
        dummy,
        name="App Config",
        description="Desc",
        mime_type="application/json",
    )
    registry.register(res)

    assert registry.contains("config://app")
    assert registry.get("config://app") == res

    # Duplicate URI raises ResourceAlreadyRegisteredError
    with pytest.raises(ResourceAlreadyRegisteredError):
        registry.register(res)


def test_resource_removal() -> None:
    """Verify resource removal and exception checks."""
    registry = ResourceRegistry()

    def dummy():
        return "data"

    res = Resource("config://app", dummy)
    registry.register(res)
    assert registry.contains("config://app")

    registry.remove("config://app")
    assert not registry.contains("config://app")

    with pytest.raises(ResourceNotFoundError):
        registry.get("config://app")

    with pytest.raises(ResourceNotFoundError):
        registry.remove("config://app")


def test_resource_listing() -> None:
    """Verify registered resource lists."""
    registry = ResourceRegistry()

    def dummy1():
        return 1

    def dummy2():
        return 2

    res1 = Resource("config://a", dummy1)
    res2 = Resource("config://b", dummy2)

    registry.register(res1)
    registry.register(res2)

    all_res = registry.list()
    assert len(all_res) == 2
    assert res1 in all_res
    assert res2 in all_res


def test_invalid_uri() -> None:
    """Verify URI scheme constraints and empty string assertions."""

    def dummy():
        pass

    # Empty URI
    with pytest.raises(ResourceRegistrationError):
        Resource("", dummy)

    # Whitespace-only URI
    with pytest.raises(ResourceRegistrationError):
        Resource("   ", dummy)

    # Invalid format (no scheme)
    with pytest.raises(ResourceRegistrationError):
        Resource("invalid-uri", dummy)

    # Invalid scheme only
    with pytest.raises(ResourceRegistrationError):
        Resource("config://", dummy)


def test_metadata_and_docstring_fallbacks() -> None:
    """Verify fallback docstrings, name formatting, and override parameters."""

    # 1. Custom description and custom name
    def dummy():
        """Original docstring."""
        return "data"

    res1 = Resource(
        "config://app",
        dummy,
        name="Custom Name",
        description="Custom Desc",
        mime_type="application/json",
    )
    assert res1.name == "Custom Name"
    assert res1.description == "Custom Desc"
    assert res1.mime_type == "application/json"

    # 2. Defaults from function docstring and function name
    res2 = Resource("config://app", dummy)
    assert res2.name == "dummy"
    assert res2.description == "Original docstring."
    assert res2.mime_type is None

    # 3. Sensible fallback if docstring is missing
    def dummy_no_doc():
        return "data"

    res3 = Resource("config://app", dummy_no_doc)
    assert res3.description == "No description provided."


def test_sync_and_async_resources() -> None:
    """Verify decorator works with sync/async methods and retains callability."""
    server = MCPServer("test")

    @server.resource("config://sync")
    def sync_res():
        return "sync_data"

    @server.resource("config://async")
    async def async_res():
        return "async_data"

    assert server.has_resource("config://sync")
    assert server.has_resource("config://async")

    assert sync_res() == "sync_data"


def test_resource_registry_isolation() -> None:
    """Verify tool and resource registries remain completely isolated."""
    server = MCPServer("test")

    @server.tool
    def my_tool(a: int) -> int:
        return a

    @server.resource("config://app")
    def my_resource():
        return "data"

    assert server.has_tool("my_tool")
    assert not server.has_tool("config://app")

    assert server.has_resource("config://app")
    assert not server.has_resource("my_tool")
