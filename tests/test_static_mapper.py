import pytest

from toolforge import MCPServer
from toolforge.intelligence import StaticToolMapper


def test_static_tool_mapper_single_tool() -> None:
    """Verify StaticToolMapper maps a single tool with 1:1 fidelity."""
    server = MCPServer("test-server")

    @server.tool(name="calculate_sum", description="Calculates the sum of two integers.")
    def add(a: int, b: int) -> int:
        return a + b

    tool = server.get_tool("calculate_sum")
    mapper = StaticToolMapper()
    result = mapper.map_tool(tool)

    assert result.name == "calculate_sum"
    assert result.original_description == "Calculates the sum of two integers."
    assert result.effective_description == "Calculates the sum of two integers."
    assert result.input_schema == tool.input_schema
    assert result.semantics is None
    assert result.is_enriched is False
    assert result.confidence == 1.0
    assert result.mapping_source == "static"


def test_static_tool_mapper_multiple_tools() -> None:
    """Verify StaticToolMapper maps a list of registered tools."""
    server = MCPServer("test-server")

    @server.tool
    def tool_alpha(x: str) -> str:
        """Alpha tool."""
        return x

    @server.tool
    def tool_beta(y: int = 10) -> int:
        """Beta tool."""
        return y

    mapper = StaticToolMapper()
    results = mapper.map_tools(server.tools)

    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"tool_alpha", "tool_beta"}
    assert all(r.mapping_source == "static" for r in results)
    assert all(r.is_enriched is False for r in results)


def test_static_tool_mapper_ambiguity_resolution() -> None:
    """Verify StaticToolMapper heuristic ambiguity resolution."""
    server = MCPServer("test-server")

    @server.tool
    def query_database(sql: str) -> list[str]:
        """Query data."""
        return []

    @server.tool
    def send_email(recipient: str, body: str) -> bool:
        """Send notification email."""
        return True

    mapper = StaticToolMapper()
    tools = server.tools

    # 1. Exact / substring match in intent
    selected, conf, rationale = mapper.resolve_ambiguity("I need to send_email to John", tools)
    assert selected.name == "send_email"
    assert conf == 0.8
    assert "send_email" in rationale

    # 2. Ambiguous intent with no name match falls back to first candidate with confidence 0.0
    selected, conf, rationale = mapper.resolve_ambiguity("Help me process this user request", tools)
    assert selected == tools[0]
    assert conf == 0.0


def test_static_tool_mapper_ambiguity_empty_candidates() -> None:
    """Verify resolve_ambiguity raises ValueError on empty candidate list."""
    mapper = StaticToolMapper()
    with pytest.raises(ValueError, match="cannot be empty"):
        mapper.resolve_ambiguity("some intent", [])
