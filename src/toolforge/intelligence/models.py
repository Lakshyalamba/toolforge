import enum
from dataclasses import dataclass, field
from typing import Any


class ToolRiskLevel(enum.StrEnum):
    """Enumeration of tool risk and mutation characteristics."""

    SAFE = "safe"  # Read-only, no side effects
    IDEMPOTENT = "idempotent"  # Modifies state, but repeating has same effect
    DESTRUCTIVE = "destructive"  # Deletes or permanently alters data
    FINANCIAL = "financial"  # Costs money, performs transactions
    UNKNOWN = "unknown"


@dataclass
class ParameterSemantics:
    """Enhanced semantic metadata for a single tool parameter."""

    name: str
    inferred_purpose: str = ""
    example_values: list[Any] = field(default_factory=list)
    common_pitfalls: str = ""


@dataclass
class ToolSemantics:
    """Enriched semantic metadata produced by LLM understanding."""

    domain: str = "general"
    category: str = "utility"
    primary_intent: str = ""
    risk_level: ToolRiskLevel = ToolRiskLevel.UNKNOWN
    improved_description: str = ""
    parameter_semantics: dict[str, ParameterSemantics] = field(default_factory=dict)
    negative_examples: list[str] = field(default_factory=list)
    confidence_score: float = 1.0


@dataclass
class ToolMappingResult:
    """Result of mapping a tool through the mapper layer."""

    name: str
    original_description: str
    effective_description: str
    input_schema: dict[str, Any]
    semantics: ToolSemantics | None = None
    is_enriched: bool = False
    confidence: float = 1.0
    mapping_source: str = "static"  # "static", "dspy", or "dspy_compiled"
