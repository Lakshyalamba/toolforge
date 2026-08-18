import anyio
import mcp.types as t
import pytest
from mcp import ClientSession
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import MCPError

from toolforge import MCPServer
from toolforge.mcp.server import MCPServerRunner


@pytest.mark.anyio
async def test_mcp_prompts_flow() -> None:
    """Verify MCP Prompts handshake, listing, get prompt, and error recovery."""
    server = MCPServer("test-prompts-server")

    @server.prompt(name="code-review", description="Generate a code review prompt")
    def code_review(language: str):
        return f"Review this {language} code."

    @server.prompt(name="explain")
    def explain(topic: str, limit: int = 10):
        return [
            {"role": "assistant", "content": "I am a teacher."},
            {"role": "user", "content": f"Explain {topic} in {limit} sentences."},
        ]

    @server.prompt(name="failing")
    def failing_prompt():
        raise RuntimeError("intentional failure")

    # Create memory streams for bidirectional connection
    server_read_send, server_read_rcv = anyio.create_memory_object_stream(20)
    client_read_send, client_read_rcv = anyio.create_memory_object_stream(20)

    runner = MCPServerRunner(server.name, server.registry, server=server)
    mcp_server = Server(server.name)

    mcp_server.add_request_handler(
        "prompts/list",
        t.PaginatedRequestParams,
        runner.adapter.handle_list_prompts,
    )
    mcp_server.add_request_handler(
        "prompts/get",
        t.GetPromptRequestParams,
        runner.adapter.handle_get_prompt,
    )

    init_options = InitializationOptions(
        server_name=server.name,
        server_version="0.1.0",
        capabilities=t.ServerCapabilities(prompts=t.PromptsCapability(list_changed=False)),
    )

    async def run_server() -> None:
        await mcp_server.run(
            server_read_rcv,
            client_read_send,
            initialization_options=init_options,
            raise_exceptions=True,
        )

    async def run_client() -> None:
        async with ClientSession(client_read_rcv, server_read_send) as session:
            # Handshake
            await session.initialize()

            # B. List Prompts
            list_res = await session.list_prompts()
            assert len(list_res.prompts) == 3

            names = {p.name for p in list_res.prompts}
            assert "code-review" in names
            assert "explain" in names
            assert "failing" in names

            # C. Verify Prompt Details
            cr_prompt = next(p for p in list_res.prompts if p.name == "code-review")
            assert cr_prompt.description == "Generate a code review prompt"
            assert len(cr_prompt.arguments) == 1
            assert cr_prompt.arguments[0].name == "language"
            assert cr_prompt.arguments[0].required is True

            # D. Get valid prompt (simple text result)
            get_res = await session.get_prompt("code-review", {"language": "Python"})
            assert len(get_res.messages) == 1
            assert get_res.messages[0].role == "user"
            assert get_res.messages[0].content.text == "Review this Python code."

            # E. Get valid prompt (multiple messages, types coercion)
            get_res2 = await session.get_prompt("explain", {"topic": "math", "limit": "5"})
            assert len(get_res2.messages) == 2
            assert get_res2.messages[0].role == "assistant"
            assert get_res2.messages[0].content.text == "I am a teacher."
            assert get_res2.messages[1].role == "user"
            assert get_res2.messages[1].content.text == "Explain math in 5 sentences."

            # F. Request unknown prompt -> raises MCPError
            with pytest.raises(MCPError) as exc_info:
                await session.get_prompt("unknown-prompt")
            assert exc_info.value.error.code == -32601
            assert "is not registered" in exc_info.value.error.message

            # G. Request failing prompt -> raises MCPError
            with pytest.raises(MCPError) as exc_info:
                await session.get_prompt("failing")
            assert exc_info.value.error.code == -32603
            assert "intentional failure" in exc_info.value.error.message

            # H. Server Remains Alive: request a valid prompt after failure
            get_recovery = await session.get_prompt("code-review", {"language": "C++"})
            assert get_recovery.messages[0].content.text == "Review this C++ code."

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        await anyio.sleep(0.1)
        await run_client()
        await client_read_send.aclose()
        await server_read_send.aclose()
