from toolforge import MCPServer
from toolforge.testing import MCPTestClient

# Define the server to be tested
server = MCPServer("demo")


@server.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@server.resource("config://app", description="App configurations")
def get_config():
    return {"name": "ToolForge", "version": "0.1.0"}


@server.prompt(name="explain")
def explain_topic(topic: str):
    """Explain a topic."""
    return f"Explain {topic} in simple terms."


# A simple test function verifying the server using MCPTestClient
def test_demo_server() -> None:
    # Use context manager for lifecycle triggers (startup/shutdown hooks)
    with MCPTestClient(server) as client:
        # 1. Test Tools listing and execution
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "add"

        result = client.call_tool("add", {"a": 10, "b": 20})
        assert result == 30

        # 2. Test Resource listing and reading
        resources = client.list_resources()
        assert len(resources) == 1
        assert resources[0].uri == "config://app"

        res_data = client.read_resource("config://app")
        assert "ToolForge" in res_data.text
        assert res_data.mime_type == "application/json"

        # 3. Test Prompt listing and retrieval
        prompts = client.list_prompts()
        assert len(prompts) == 1
        assert prompts[0].name == "explain"

        prompt_data = client.get_prompt("explain", {"topic": "MCP"})
        assert len(prompt_data.messages) == 1
        assert prompt_data.messages[0].content == "Explain MCP in simple terms."
        assert prompt_data.messages[0].role == "user"


if __name__ == "__main__":
    print("Running MCPTestClient example checks...")
    test_demo_server()
    print("All checks passed successfully!")
