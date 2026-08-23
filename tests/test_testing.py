import pytest

from mcptoolforge import (
    MCPServer,
    ResourceExecutionError,
    ResourceNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from mcptoolforge.testing import MCPTestClient, MCPToolForgeTestingError


def test_test_client_creation_and_isolation() -> None:
    """Verify separate server instances do not share tools, resources, or prompts."""
    server1 = MCPServer("server1")
    server2 = MCPServer("server2")

    @server1.tool
    def add(a: int, b: int) -> int:
        return a + b

    client1 = MCPTestClient(server1)
    client2 = MCPTestClient(server2)

    assert len(client1.list_tools()) == 1
    assert len(client2.list_tools()) == 0


def test_sync_tool_operations() -> None:
    """Verify tool listing, execution, parameter validations, and missing tool handling."""
    server = MCPServer("test")

    @server.tool
    def multiply(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    client = MCPTestClient(server)

    # list_tools
    tools = client.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "multiply"
    assert tools[0].description == "Multiply two numbers."

    # call_tool
    assert client.call_tool("multiply", {"x": 3, "y": 4}) == 12

    # tool validation error - missing argument
    with pytest.raises(ToolValidationError) as exc:
        client.call_tool("multiply", {"x": 3})
    assert "missing required parameter" in str(exc.value)

    # tool validation error - invalid type
    with pytest.raises(ToolValidationError) as exc:
        client.call_tool("multiply", {"x": 3, "y": "wrong"})
    assert "expected integer" in str(exc.value)

    # tool validation error - unexpected argument
    with pytest.raises(ToolValidationError) as exc:
        client.call_tool("multiply", {"x": 3, "y": 4, "z": 5})
    assert "unexpected parameter" in str(exc.value)

    # unknown tool raises ToolNotFoundError
    with pytest.raises(ToolNotFoundError):
        client.call_tool("nonexistent")


def test_tool_execution_error() -> None:
    """Verify original execution failures propagate cleanly wrapped in ToolExecutionError."""
    server = MCPServer("test")

    @server.tool
    def failing():
        raise ValueError("failing tool")

    client = MCPTestClient(server)
    with pytest.raises(ToolExecutionError) as exc:
        client.call_tool("failing")
    assert "failing tool" in str(exc.value)


def test_middleware_execution() -> None:
    """Verify that middlewares run correctly when calling tools via the test client."""
    server = MCPServer("test")
    events = []

    @server.middleware
    def logger(context, next_fn):
        events.append("before")
        res = next_fn()
        events.append("after")
        return res

    @server.tool
    def hello() -> str:
        events.append("execute")
        return "hi"

    client = MCPTestClient(server)
    assert client.call_tool("hello") == "hi"
    assert events == ["before", "execute", "after"]


def test_resource_operations() -> None:
    """Verify resource listing, reading, type mapping, and missing resource errors."""
    server = MCPServer("test")

    @server.resource("config://app", description="App Config")
    def config():
        return {"name": "MCPToolForge"}

    @server.resource("data://text")
    def text():
        return "hello world"

    @server.resource("data://blob")
    def blob():
        return b"binary"

    @server.resource("test://failing")
    def failing():
        raise RuntimeError("failed resource")

    client = MCPTestClient(server)

    # list_resources
    resources = client.list_resources()
    assert len(resources) == 4
    uris = {r.uri for r in resources}
    assert "config://app" in uris

    # read_resource (json dict)
    res_dict = client.read_resource("config://app")
    assert res_dict.uri == "config://app"
    assert res_dict.text == '{"name": "MCPToolForge"}'
    assert res_dict.mime_type == "application/json"
    assert not res_dict.is_blob

    # read_resource (string)
    res_text = client.read_resource("data://text")
    assert res_text.text == "hello world"

    # read_resource (blob)
    res_blob = client.read_resource("data://blob")
    assert res_blob.blob == "YmluYXJ5"  # base64 for b"binary"
    assert res_blob.is_blob

    # unknown resource raises ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError):
        client.read_resource("config://unknown")

    # resource execution error
    with pytest.raises(ResourceExecutionError) as exc:
        client.read_resource("test://failing")
    assert "failed resource" in str(exc.value)


def test_prompt_operations() -> None:
    """Verify prompt listing, retrieval mapping, validation coercion, and execution failures."""
    server = MCPServer("test")

    @server.prompt(name="code-review", description="review code")
    def review(language: str):
        return f"Review {language} code."

    @server.prompt(name="failing")
    def failing():
        raise RuntimeError("failed prompt")

    client = MCPTestClient(server)

    # list_prompts
    prompts = client.list_prompts()
    assert len(prompts) == 2
    assert prompts[0].name == "code-review"

    # get_prompt
    res = client.get_prompt("code-review", {"language": "Python"})
    assert len(res.messages) == 1
    assert res.messages[0].role == "user"
    assert res.messages[0].content == "Review Python code."
    assert res.description == "review code"

    # unknown prompt raises ToolNotFoundError
    with pytest.raises(ToolNotFoundError):
        client.get_prompt("unknown")

    # prompt execution error
    with pytest.raises(ToolExecutionError) as exc:
        client.get_prompt("failing")
    assert "failed prompt" in str(exc.value)


@pytest.mark.anyio
async def test_async_operations() -> None:
    """Verify asynchronous operations on tools, resources, and prompts."""
    server = MCPServer("test")

    @server.tool
    async def fetch(url: str) -> str:
        return f"content of {url}"

    @server.resource("config://app")
    async def async_resource():
        return "async data"

    @server.prompt(name="code-review")
    async def async_prompt(language: str):
        return f"Review {language}"

    client = MCPTestClient(server)

    # call_tool_async
    res_tool = await client.call_tool_async("fetch", {"url": "http://example.com"})
    assert res_tool == "content of http://example.com"

    # read_resource_async
    res_res = await client.read_resource_async("config://app")
    assert res_res.text == "async data"

    # get_prompt_async
    res_prompt = await client.get_prompt_async("code-review", {"language": "Go"})
    assert res_prompt.messages[0].content == "Review Go"

    # Calling sync methods inside running loop should raise MCPToolForgeTestingError
    with pytest.raises(MCPToolForgeTestingError):
        client.call_tool("fetch", {"url": "http://example.com"})


def test_lifecycle_context_manager() -> None:
    """Verify sync context manager triggers on_startup and on_shutdown hooks."""
    server = MCPServer("test")
    events = []

    @server.on_startup
    def startup():
        events.append("startup")

    @server.on_shutdown
    def shutdown():
        events.append("shutdown")

    with MCPTestClient(server) as client:
        assert isinstance(client, MCPTestClient)
        events.append("run")

    assert events == ["startup", "run", "shutdown"]


@pytest.mark.anyio
async def test_async_lifecycle_context_manager() -> None:
    """Verify async context manager triggers async on_startup and on_shutdown hooks."""
    server = MCPServer("test")
    events = []

    @server.on_startup
    async def startup():
        events.append("async_startup")

    @server.on_shutdown
    async def shutdown():
        events.append("async_shutdown")

    async with MCPTestClient(server) as client:
        assert isinstance(client, MCPTestClient)
        events.append("run")

    assert events == ["async_startup", "run", "async_shutdown"]
