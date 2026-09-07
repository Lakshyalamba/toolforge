from typing import Any
from unittest.mock import MagicMock

import pytest

from toolforge import MCPServer
from toolforge.intelligence import (
    DSPyNotInstalledError,
    DSPyToolMapper,
    StaticToolMapper,
    ToolMappingError,
    ToolRiskLevel,
    is_dspy_available,
)
from toolforge.intelligence.signatures import (
    ToolClassificationSignature,
    ToolDescriptionImprovementSignature,
    ToolUnderstandingSignature,
)


def test_is_dspy_available() -> None:
    """Verify is_dspy_available returns a valid boolean."""
    avail = is_dspy_available()
    assert isinstance(avail, bool)


def test_dspy_signatures_raise_when_dspy_missing() -> None:
    """Verify that placeholder signatures raise DSPyNotInstalledError when instantiated."""
    if not is_dspy_available():
        with pytest.raises(DSPyNotInstalledError, match="DSPy is not installed"):
            ToolUnderstandingSignature()

        with pytest.raises(DSPyNotInstalledError, match="DSPy is not installed"):
            ToolClassificationSignature()

        with pytest.raises(DSPyNotInstalledError, match="DSPy is not installed"):
            ToolDescriptionImprovementSignature()


def test_dspy_tool_mapper_uninstalled_fallback() -> None:
    """Verify DSPyToolMapper falls back cleanly to StaticToolMapper when dspy is not installed."""
    if not is_dspy_available():
        server = MCPServer("test-server")

        @server.tool
        def multiply(a: int, b: int) -> int:
            """Multiply two numbers."""
            return a * b

        tool = server.get_tool("multiply")
        mapper = DSPyToolMapper(strict=False)

        assert mapper.is_dspy_ready is False

        # Should fall back to static mapping without error
        result = mapper.map_tool(tool)
        assert result.name == "multiply"
        assert result.effective_description == "Multiply two numbers."
        assert result.is_enriched is False
        assert result.mapping_source == "static"

        # Multi-tool mapping
        results = mapper.map_tools(server.tools)
        assert len(results) == 1
        assert results[0].is_enriched is False

        # Ambiguity resolution fallback
        selected, conf, _ = mapper.resolve_ambiguity("I need to multiply values", server.tools)
        assert selected.name == "multiply"
        assert conf > 0


def test_dspy_tool_mapper_uninstalled_strict_mode() -> None:
    """Verify DSPyToolMapper raises DSPyNotInstalledError when strict=True and dspy is absent."""
    if not is_dspy_available():
        with pytest.raises(DSPyNotInstalledError, match="DSPy is not installed"):
            DSPyToolMapper(strict=True)


def test_dspy_tool_mapper_mocked_enrichment_success() -> None:
    """Verify DSPyToolMapper properly unpacks structured predictions when DSPy is active."""
    server = MCPServer("test-server")

    @server.tool
    def purge_records(table: str, older_than_days: int = 30) -> int:
        """Purge old records."""
        return 0

    tool = server.get_tool("purge_records")

    # Create a mock enricher prediction
    mock_prediction = MagicMock()
    mock_prediction.domain = "database"
    mock_prediction.category = "mutation"
    mock_prediction.risk_level = "destructive"
    mock_prediction.primary_intent = "Permanently purge records older than the given days threshold"
    mock_prediction.improved_description = (
        "Permanently purges table records older than older_than_days. "
        "Caution: this deletion is irreversible."
    )
    mock_prediction.negative_examples = ["Do not use for read queries or analytics."]
    mock_prediction.confidence = 0.95

    mock_enricher = MagicMock(return_value=mock_prediction)
    mock_disambiguator = MagicMock()

    mapper = DSPyToolMapper(
        confidence_threshold=0.7,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )

    assert mapper.is_dspy_ready is True
    result = mapper.map_tool(tool)

    assert result.is_enriched is True
    assert result.mapping_source == "dspy"
    assert result.confidence == 0.95
    assert result.effective_description == mock_prediction.improved_description
    assert result.original_description == "Purge old records."

    assert result.semantics is not None
    assert result.semantics.domain == "database"
    assert result.semantics.category == "mutation"
    assert result.semantics.risk_level == ToolRiskLevel.DESTRUCTIVE
    assert len(result.semantics.negative_examples) == 1


def test_dspy_tool_mapper_low_confidence_fallback() -> None:
    """Verify that predictions below the confidence threshold fall back to static mapping."""
    server = MCPServer("test-server")

    @server.tool
    def vague_tool(data: Any) -> Any:
        """Processes data."""
        return data

    tool = server.get_tool("vague_tool")

    mock_prediction = MagicMock()
    mock_prediction.confidence = 0.4  # Below threshold 0.7
    mock_enricher = MagicMock(return_value=mock_prediction)
    mock_disambiguator = MagicMock()

    # 1. Non-strict: falls back to static mapper
    mapper = DSPyToolMapper(
        confidence_threshold=0.7,
        strict=False,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )
    result = mapper.map_tool(tool)
    assert result.is_enriched is False
    assert result.mapping_source == "static"
    assert result.effective_description == "Processes data."

    # 2. Strict: raises ToolMappingError
    strict_mapper = DSPyToolMapper(
        confidence_threshold=0.7,
        strict=True,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )
    with pytest.raises(ToolMappingError, match="below threshold"):
        strict_mapper.map_tool(tool)


def test_dspy_tool_mapper_exception_recovery() -> None:
    """Verify that LLM/runtime exceptions during enrichment trigger fallback."""
    server = MCPServer("test-server")

    @server.tool
    def simple_tool(x: int) -> int:
        """Simple tool."""
        return x

    tool = server.get_tool("simple_tool")

    mock_enricher = MagicMock(side_effect=RuntimeError("LLM rate limit reached"))
    mock_disambiguator = MagicMock()

    # 1. Non-strict falls back
    mapper = DSPyToolMapper(
        strict=False,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )
    result = mapper.map_tool(tool)
    assert result.is_enriched is False
    assert result.mapping_source == "static"

    # 2. Strict raises ToolMappingError
    strict_mapper = DSPyToolMapper(
        strict=True,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )
    with pytest.raises(ToolMappingError, match="LLM rate limit reached"):
        strict_mapper.map_tool(tool)


def test_dspy_tool_mapper_disambiguation() -> None:
    """Verify semantic ambiguity resolution using mock disambiguator."""
    server = MCPServer("test-server")

    @server.tool
    def search_docs(query: str) -> list[str]:
        """Search documentation."""
        return []

    @server.tool
    def search_code(query: str) -> list[str]:
        """Search source code."""
        return []

    mock_enricher = MagicMock()
    mock_pred = MagicMock()
    mock_pred.selected_tool = "search_code"
    mock_pred.confidence = 0.92
    mock_pred.rationale = "User query specifically asks for function implementation"

    mock_disambiguator = MagicMock(return_value=mock_pred)

    mapper = DSPyToolMapper(
        confidence_threshold=0.7,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )

    selected, conf, rationale = mapper.resolve_ambiguity(
        "Find where validate_tool_arguments is implemented", server.tools
    )
    assert selected.name == "search_code"
    assert conf == 0.92
    assert "function implementation" in rationale


def test_dspy_tool_mapper_disambiguation_low_confidence_fallback() -> None:
    """Verify ambiguity resolution fallback when confidence is insufficient."""
    server = MCPServer("test-server")

    @server.tool
    def tool_a() -> None:
        pass

    @server.tool
    def tool_b() -> None:
        pass

    mock_enricher = MagicMock()
    mock_pred = MagicMock()
    mock_pred.selected_tool = "tool_a"
    mock_pred.confidence = 0.3  # Below 0.7 threshold

    mock_disambiguator = MagicMock(return_value=mock_pred)

    # 1. Non-strict: falls back to static heuristic
    mapper = DSPyToolMapper(
        confidence_threshold=0.7,
        strict=False,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )
    selected, conf, _ = mapper.resolve_ambiguity("Run tool_a please", server.tools)
    # Static mapper matches "tool_a" in intent string
    assert selected.name == "tool_a"
    assert conf == 0.8  # Static confidence

    # 2. Strict: raises ToolMappingError
    strict_mapper = DSPyToolMapper(
        confidence_threshold=0.7,
        strict=True,
        enricher_module=mock_enricher,
        disambiguator_module=mock_disambiguator,
    )
    with pytest.raises(ToolMappingError, match="Ambiguity resolution failed"):
        strict_mapper.resolve_ambiguity("Run tool_a please", server.tools)


def test_dspy_tool_mapper_custom_fallback() -> None:
    """Verify DSPyToolMapper delegates to custom fallback mapper when provided."""
    server = MCPServer("test-server")

    @server.tool
    def hello() -> str:
        """Hello doc."""
        return "hi"

    tool = server.get_tool("hello")

    custom_fallback = StaticToolMapper()
    custom_fallback.map_tool = MagicMock(wraps=custom_fallback.map_tool)  # type: ignore[assignment]

    mock_enricher = MagicMock(side_effect=Exception("Crash"))
    mapper = DSPyToolMapper(
        fallback_mapper=custom_fallback,
        enricher_module=mock_enricher,
        disambiguator_module=MagicMock(),
    )

    result = mapper.map_tool(tool)
    assert result.name == "hello"
    custom_fallback.map_tool.assert_called_once_with(tool)


def test_dspy_tool_mapper_caching() -> None:
    """Verify DSPyToolMapper caches mapping results and supports cache clearing."""
    server = MCPServer("cache-server")

    @server.tool
    def calculate(x: int) -> int:
        """Calculate something."""
        return x * 2

    tool = server.get_tool("calculate")

    mock_prediction = MagicMock()
    mock_prediction.domain = "math"
    mock_prediction.category = "calculation"
    mock_prediction.primary_intent = "multiply"
    mock_prediction.risk_level = "safe"
    mock_prediction.improved_description = "Calculates twice x"
    mock_prediction.negative_examples = []
    mock_prediction.confidence = 0.95

    mock_enricher = MagicMock(return_value=mock_prediction)
    mapper = DSPyToolMapper(
        enricher_module=mock_enricher,
        disambiguator_module=MagicMock(),
        enable_cache=True,
    )

    # 1. First call - populates cache
    res1 = mapper.map_tool(tool)
    assert res1.is_enriched is True
    assert mock_enricher.call_count == 1

    # 2. Second call with same tool - hits cache
    res2 = mapper.map_tool(tool)
    assert res2 is res1
    assert mock_enricher.call_count == 1

    # 3. Clear cache - re-queries enricher
    mapper.clear_cache()
    res3 = mapper.map_tool(tool)
    assert mock_enricher.call_count == 2
    assert res3.name == "calculate"

    # 4. Cache disabled
    mock_enricher.reset_mock()
    no_cache_mapper = DSPyToolMapper(
        enricher_module=mock_enricher,
        disambiguator_module=MagicMock(),
        enable_cache=False,
    )
    no_cache_mapper.map_tool(tool)
    no_cache_mapper.map_tool(tool)
    assert mock_enricher.call_count == 2


def test_dspy_tool_mapper_concurrent_map_tools() -> None:
    """Verify map_tools maps multiple tools concurrently without error."""
    server = MCPServer("concurrent-server")

    @server.tool
    def tool_1(a: int) -> int:
        """Tool 1 doc."""
        return a

    @server.tool
    def tool_2(b: str) -> str:
        """Tool 2 doc."""
        return b

    @server.tool
    def tool_3(c: float) -> float:
        """Tool 3 doc."""
        return c

    mock_prediction = MagicMock()
    mock_prediction.domain = "test"
    mock_prediction.category = "test"
    mock_prediction.primary_intent = "test"
    mock_prediction.risk_level = "safe"
    mock_prediction.improved_description = "Enriched"
    mock_prediction.negative_examples = []
    mock_prediction.confidence = 0.9

    mock_enricher = MagicMock(return_value=mock_prediction)
    mapper = DSPyToolMapper(
        enricher_module=mock_enricher,
        disambiguator_module=MagicMock(),
    )

    results = mapper.map_tools(server.tools)
    assert len(results) == 3
    assert [r.name for r in results] == ["tool_1", "tool_2", "tool_3"]
    assert all(r.is_enriched for r in results)


def test_toolforge_config_create_mapper_uses_from_config() -> None:
    """Verify ToolForgeConfig.create_mapper delegates properly through from_config."""
    from toolforge.config import DSPyConfig, ToolForgeConfig

    cfg = ToolForgeConfig(
        name="test_app",
        dspy=DSPyConfig(enabled=True, confidence_threshold=0.85),
    )
    mapper = cfg.create_mapper()
    assert isinstance(mapper, DSPyToolMapper)
    assert mapper.confidence_threshold == 0.85
