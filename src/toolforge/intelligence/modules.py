import json
from typing import Any

from toolforge.intelligence.errors import DSPyNotInstalledError

try:
    import dspy

    _HAS_DSPY = True
except ImportError:
    dspy = None
    _HAS_DSPY = False


if _HAS_DSPY:
    from toolforge.intelligence.signatures import (
        SemanticMappingSignature,
        ToolClassificationSignature,
        ToolDescriptionImprovementSignature,
        ToolUnderstandingSignature,
    )

    class ToolEnricherModule(dspy.Module):
        """Composite DSPy module for understanding, classifying, and improving tool descriptions."""

        def __init__(self) -> None:
            super().__init__()
            self.classifier = dspy.ChainOfThought(ToolClassificationSignature)
            self.understander = dspy.ChainOfThought(ToolUnderstandingSignature)
            self.improver = dspy.ChainOfThought(ToolDescriptionImprovementSignature)

        def forward(
            self, tool_name: str, docstring: str, input_schema: str | dict[str, Any]
        ) -> dspy.Prediction:
            schema_str = (
                json.dumps(input_schema) if isinstance(input_schema, dict) else str(input_schema)
            )

            # 1. Classify domain, category, and risk
            classification = self.classifier(
                tool_name=tool_name,
                docstring=docstring,
                input_schema=schema_str,
            )

            # 2. Extract deep intent, prerequisites, and return characteristics
            understanding = self.understander(
                tool_name=tool_name,
                docstring=docstring,
                input_schema=schema_str,
            )

            # 3. Generate improved description engineered for LLM tool calling
            improvement = self.improver(
                tool_name=tool_name,
                current_description=docstring,
                input_schema=schema_str,
                domain=getattr(classification, "domain", "general"),
                risk_level=getattr(classification, "risk_level", "unknown"),
            )

            raw_confidence = getattr(improvement, "confidence", 0.8)
            try:
                confidence_score = float(raw_confidence)
            except (ValueError, TypeError):
                confidence_score = 0.8

            neg_examples_raw = getattr(improvement, "negative_examples", "")
            if isinstance(neg_examples_raw, list):
                negative_examples = [str(x) for x in neg_examples_raw]
            elif isinstance(neg_examples_raw, str) and neg_examples_raw.strip():
                negative_examples = [
                    line.strip().lstrip("-•* ")
                    for line in neg_examples_raw.splitlines()
                    if line.strip()
                ]
            else:
                negative_examples = []

            return dspy.Prediction(
                domain=getattr(classification, "domain", "general").strip().lower(),
                category=getattr(classification, "category", "utility").strip().lower(),
                risk_level=getattr(classification, "risk_level", "unknown").strip().lower(),
                risk_rationale=getattr(classification, "rationale", ""),
                primary_intent=getattr(understanding, "primary_intent", "").strip(),
                prerequisites=getattr(understanding, "prerequisites", "").strip(),
                return_summary=getattr(understanding, "return_summary", "").strip(),
                improved_description=getattr(improvement, "improved_description", "").strip(),
                negative_examples=negative_examples,
                confidence=max(0.0, min(1.0, confidence_score)),
            )

    class ToolDisambiguatorModule(dspy.Module):
        """DSPy module for resolving semantic ambiguities and selecting the best matching tool."""

        def __init__(self) -> None:
            super().__init__()
            self.selector = dspy.ChainOfThought(SemanticMappingSignature)

        def forward(self, intent: str, candidate_tools: list[str]) -> dspy.Prediction:
            candidates_formatted = "\n---\n".join(candidate_tools)
            prediction = self.selector(
                intent=intent,
                candidate_tools=candidates_formatted,
            )

            raw_confidence = getattr(prediction, "confidence", 0.7)
            try:
                confidence_score = float(raw_confidence)
            except (ValueError, TypeError):
                confidence_score = 0.7

            return dspy.Prediction(
                selected_tool=getattr(prediction, "selected_tool", "").strip(),
                confidence=max(0.0, min(1.0, confidence_score)),
                rationale=getattr(prediction, "rationale", "").strip(),
                extracted_arguments=getattr(prediction, "extracted_arguments", "{}").strip(),
            )

else:

    class _MissingDSPyModule:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise DSPyNotInstalledError(
                "DSPy is not installed. Install it via 'pip install \"mcptoolforge[dspy]\"'."
            )

    ToolEnricherModule = _MissingDSPyModule  # type: ignore[assignment, misc]
    ToolDisambiguatorModule = _MissingDSPyModule  # type: ignore[assignment, misc]
