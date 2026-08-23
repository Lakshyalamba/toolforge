import pytest

from mcptoolforge import (
    MCPServer,
    ToolAlreadyRegisteredError,
    ToolNotFoundError,
    ToolRegistrationError,
    ToolValidationError,
)
from mcptoolforge.prompts import Prompt, PromptRegistry
from mcptoolforge.validation import validate_prompt_arguments


def test_prompt_registration_and_lookup() -> None:
    """Verify prompt registration, lookup, and collision handling."""
    registry = PromptRegistry()

    def dummy():
        return "prompt text"

    pr = Prompt(dummy, name="my-prompt", description="Prompt Description")
    registry.register(pr)

    assert registry.contains("my-prompt")
    assert registry.get("my-prompt") == pr

    # Duplicate names raises ToolAlreadyRegisteredError
    with pytest.raises(ToolAlreadyRegisteredError):
        registry.register(pr)


def test_prompt_removal() -> None:
    """Verify prompt deletion and lookup failure triggers."""
    registry = PromptRegistry()

    def dummy():
        return "data"

    pr = Prompt(dummy)
    registry.register(pr)
    assert registry.contains("dummy")

    registry.remove("dummy")
    assert not registry.contains("dummy")

    with pytest.raises(ToolNotFoundError):
        registry.get("dummy")

    with pytest.raises(ToolNotFoundError):
        registry.remove("dummy")


def test_prompt_listing() -> None:
    """Verify registered prompts lists."""
    registry = PromptRegistry()

    def dummy1():
        return 1

    def dummy2():
        return 2

    pr1 = Prompt(dummy1, name="a")
    pr2 = Prompt(dummy2, name="b")

    registry.register(pr1)
    registry.register(pr2)

    all_pr = registry.list()
    assert len(all_pr) == 2
    assert pr1 in all_pr
    assert pr2 in all_pr


def test_invalid_names() -> None:
    """Verify prompt naming conventions validations."""

    def dummy():
        pass

    # Empty name
    with pytest.raises(ToolRegistrationError):
        Prompt(dummy, name="")

    # Whitespace-only name
    with pytest.raises(ToolRegistrationError):
        Prompt(dummy, name="   ")

    # Invalid characters
    with pytest.raises(ToolRegistrationError):
        Prompt(dummy, name="invalid name spaces")


def test_metadata_and_docstring_fallbacks() -> None:
    """Verify docstring overrides and fallback string behaviors."""

    # 1. Custom description and custom name
    def dummy():
        """Original docstring."""
        return "data"

    pr1 = Prompt(dummy, name="custom-name", description="Custom Desc")
    assert pr1.name == "custom-name"
    assert pr1.description == "Custom Desc"

    # 2. Defaults from function docstring and function name
    pr2 = Prompt(dummy)
    assert pr2.name == "dummy"
    assert pr2.description == "Original docstring."

    # 3. Sensible fallback if docstring is missing
    def dummy_no_doc():
        return "data"

    pr3 = Prompt(dummy_no_doc)
    assert pr3.description == "No description provided."


def test_prompt_argument_validation_and_coercion() -> None:
    """Verify argument validations, unexpected keys checks, and type coercions."""

    def dummy(topic: str, limit: int = 10, verbose: bool = False):
        return f"{topic} {limit} {verbose}"

    pr = Prompt(dummy)

    # Valid string arguments coerced correctly
    args = {"topic": "AI", "limit": "5", "verbose": "true"}
    val_args = validate_prompt_arguments(pr, args)
    assert val_args == {"topic": "AI", "limit": 5, "verbose": True}

    # Missing required argument
    with pytest.raises(ToolValidationError):
        validate_prompt_arguments(pr, {"limit": "5"})

    # Unexpected argument
    with pytest.raises(ToolValidationError):
        validate_prompt_arguments(pr, {"topic": "AI", "extra": "yes"})


def test_sync_and_async_prompts() -> None:
    """Verify decorator works with sync/async prompts and preserves callability."""
    server = MCPServer("test")

    @server.prompt
    def sync_pr(topic: str):
        return f"Explain {topic}"

    @server.prompt
    async def async_pr(topic: str):
        return f"Review {topic}"

    assert server.has_prompt("sync_pr")
    assert server.has_prompt("async_pr")

    assert sync_pr("math") == "Explain math"


def test_prompt_registry_isolation() -> None:
    """Verify registries isolation between tools, resources, and prompts."""
    server = MCPServer("test")

    @server.tool
    def my_tool(a: int) -> int:
        return a

    @server.resource("config://app")
    def my_resource():
        return "data"

    @server.prompt
    def my_prompt():
        return "prompt"

    assert server.has_tool("my_tool")
    assert not server.has_tool("my_prompt")

    assert server.has_resource("config://app")
    assert not server.has_resource("my_prompt")

    assert server.has_prompt("my_prompt")
    assert not server.has_prompt("my_tool")
    assert not server.has_prompt("config://app")
