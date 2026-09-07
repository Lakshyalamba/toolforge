from toolforge.intelligence.errors import (
    DSPyNotInstalledError,
    IntelligenceError,
    ToolMappingError,
)
from toolforge.intelligence.models import (
    ParameterSemantics,
    ToolMappingResult,
    ToolRiskLevel,
    ToolSemantics,
)


def test_tool_risk_level_values() -> None:
    """Test ToolRiskLevel enum members and string values."""
    assert ToolRiskLevel.SAFE == "safe"
    assert ToolRiskLevel.IDEMPOTENT == "idempotent"
    assert ToolRiskLevel.DESTRUCTIVE == "destructive"
    assert ToolRiskLevel.FINANCIAL == "financial"
    assert ToolRiskLevel.UNKNOWN == "unknown"


def test_parameter_semantics() -> None:
    """Test ParameterSemantics dataclass defaults and properties."""
    param = ParameterSemantics(
        name="user_id",
        inferred_purpose="Primary key identifier for user",
        example_values=[1, 42, 100],
        common_pitfalls="Do not pass string IDs",
    )
    assert param.name == "user_id"
    assert param.inferred_purpose == "Primary key identifier for user"
    assert param.example_values == [1, 42, 100]
    assert param.common_pitfalls == "Do not pass string IDs"


def test_tool_semantics_defaults() -> None:
    """Test ToolSemantics with default parameters."""
    sem = ToolSemantics()
    assert sem.domain == "general"
    assert sem.category == "utility"
    assert sem.primary_intent == ""
    assert sem.risk_level == ToolRiskLevel.UNKNOWN
    assert sem.improved_description == ""
    assert sem.parameter_semantics == {}
    assert sem.negative_examples == []
    assert sem.confidence_score == 1.0


def test_tool_semantics_custom() -> None:
    """Test ToolSemantics with custom semantic metadata."""
    sem = ToolSemantics(
        domain="database",
        category="mutation",
        primary_intent="Permanently deletes a row",
        risk_level=ToolRiskLevel.DESTRUCTIVE,
        improved_description="Permanently delete a record by ID.",
        negative_examples=["Do not use for read queries"],
        confidence_score=0.95,
    )
    assert sem.domain == "database"
    assert sem.category == "mutation"
    assert sem.risk_level == ToolRiskLevel.DESTRUCTIVE
    assert sem.confidence_score == 0.95
    assert len(sem.negative_examples) == 1


def test_tool_mapping_result() -> None:
    """Test ToolMappingResult creation and attributes."""
    result = ToolMappingResult(
        name="delete_user",
        original_description="Delete user.",
        effective_description="Permanently delete user record.",
        input_schema={"type": "object", "properties": {"user_id": {"type": "integer"}}},
        is_enriched=True,
        confidence=0.92,
        mapping_source="dspy",
    )
    assert result.name == "delete_user"
    assert result.effective_description == "Permanently delete user record."
    assert result.is_enriched is True
    assert result.confidence == 0.92
    assert result.mapping_source == "dspy"


def test_intelligence_errors() -> None:
    """Verify intelligence error inheritance."""
    assert issubclass(DSPyNotInstalledError, IntelligenceError)
    assert issubclass(ToolMappingError, IntelligenceError)
