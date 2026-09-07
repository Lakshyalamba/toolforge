from toolforge.intelligence.mapper.base import ToolMapper
from toolforge.intelligence.models import ToolMappingResult
from toolforge.registry import Tool


class StaticToolMapper(ToolMapper):
    """Deterministic, zero-overhead tool mapper.

    Performs 1:1 passthrough of tool docstrings, names, and JSON schemas
    without invoking any Language Models or external AI dependencies.
    """

    def map_tool(self, tool: Tool) -> ToolMappingResult:
        """Map a Tool deterministically to a ToolMappingResult."""
        return ToolMappingResult(
            name=tool.name,
            original_description=tool.description,
            effective_description=tool.description,
            input_schema=tool.input_schema,
            semantics=None,
            is_enriched=False,
            confidence=1.0,
            mapping_source="static",
        )

    def map_tools(self, tools: list[Tool]) -> list[ToolMappingResult]:
        """Map a list of tools deterministically."""
        return [self.map_tool(t) for t in tools]

    def resolve_ambiguity(
        self, intent: str, candidate_tools: list[Tool]
    ) -> tuple[Tool, float, str]:
        """Resolve ambiguity using deterministic lexical matching.

        Checks if any candidate tool's name is mentioned in the intent string.
        Defaults to the first candidate tool with 0.0 confidence if no heuristic match is found.
        """
        if not candidate_tools:
            raise ValueError("Candidate tools list cannot be empty.")

        normalized_intent = intent.lower()
        for t in candidate_tools:
            if t.name.lower() in normalized_intent:
                return t, 0.8, f"Heuristic lexical match: tool name '{t.name}' found in intent."

        first = candidate_tools[0]
        return (
            first,
            0.0,
            f"Default static fallback: no heuristic match found; first candidate '{first.name}'.",
        )
