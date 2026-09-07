from typing import Any

from toolforge.intelligence.errors import DSPyNotInstalledError

try:
    import dspy

    _HAS_DSPY = True
except ImportError:
    dspy = None
    _HAS_DSPY = False


if _HAS_DSPY:

    class ToolUnderstandingSignature(dspy.Signature):
        """Understand the primary intent, prerequisites, and return semantics of a tool."""

        tool_name: str = dspy.InputField(desc="The name of the tool")
        docstring: str = dspy.InputField(desc="The existing tool docstring or description")
        input_schema: str = dspy.InputField(desc="JSON schema string of the tool parameters")

        primary_intent: str = dspy.OutputField(
            desc="Clear, concise single-sentence summary of what this tool accomplishes"
        )
        prerequisites: str = dspy.OutputField(
            desc="Any prerequisites or assumptions required before calling the tool"
        )
        return_summary: str = dspy.OutputField(
            desc="Summary of what data or result the tool returns"
        )

    class ToolClassificationSignature(dspy.Signature):
        """Classify a tool into functional domain, operational category, and risk level."""

        tool_name: str = dspy.InputField(desc="The name of the tool")
        docstring: str = dspy.InputField(desc="The existing tool docstring or description")
        input_schema: str = dspy.InputField(desc="JSON schema string of the tool parameters")

        domain: str = dspy.OutputField(
            desc="Functional domain e.g. database, web, filesystem, math, utility"
        )
        category: str = dspy.OutputField(
            desc="Operational category e.g. query, mutation, analytics, configuration"
        )
        risk_level: str = dspy.OutputField(
            desc="Risk assessment: safe, idempotent, destructive, financial, unknown"
        )
        rationale: str = dspy.OutputField(desc="Brief rationale for the risk classification")

    class SemanticMappingSignature(dspy.Signature):
        """Semantically select the best tool for a user intent and extract arguments."""

        intent: str = dspy.InputField(desc="The user goal or query in natural language")
        candidate_tools: str = dspy.InputField(
            desc="List of candidate tools with their descriptions and schemas"
        )

        selected_tool: str = dspy.OutputField(desc="Name of the best matching tool")
        confidence: float = dspy.OutputField(
            desc="Confidence score from 0.0 to 1.0 for this tool selection"
        )
        rationale: str = dspy.OutputField(
            desc="Explanation of why this tool was selected over others"
        )
        extracted_arguments: str = dspy.OutputField(
            desc="JSON string containing extracted arguments for the selected tool"
        )

    class ToolDescriptionImprovementSignature(dspy.Signature):
        """Generate an enriched, LLM-optimized description for a tool."""

        tool_name: str = dspy.InputField(desc="The name of the tool")
        current_description: str = dspy.InputField(desc="The current tool description or docstring")
        input_schema: str = dspy.InputField(desc="JSON schema string of the tool parameters")
        domain: str = dspy.InputField(desc="Functional domain of the tool")
        risk_level: str = dspy.InputField(desc="Risk level of the tool")

        improved_description: str = dspy.OutputField(
            desc="Optimized description engineered for downstream LLM function calling"
        )
        negative_examples: str = dspy.OutputField(
            desc="Scenarios or user requests where this tool should NOT be used"
        )
        confidence: float = dspy.OutputField(desc="Confidence score between 0.0 and 1.0")

else:

    class _MissingDSPySignature:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise DSPyNotInstalledError(
                "DSPy is not installed. Install it via 'pip install \"mcptoolforge[dspy]\"'."
            )

    ToolUnderstandingSignature = _MissingDSPySignature  # type: ignore[assignment, misc]
    ToolClassificationSignature = _MissingDSPySignature  # type: ignore[assignment, misc]
    SemanticMappingSignature = _MissingDSPySignature  # type: ignore[assignment, misc]
    ToolDescriptionImprovementSignature = _MissingDSPySignature  # type: ignore[assignment, misc]
