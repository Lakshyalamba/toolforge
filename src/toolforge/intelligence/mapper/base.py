from abc import ABC, abstractmethod

from toolforge.intelligence.models import ToolMappingResult
from toolforge.registry import Tool


class ToolMapper(ABC):
    """Abstract base class for mapping and enriching ToolForge tools.

    Provides the contract for both deterministic static mapping and
    intelligent DSPy-based semantic mapping.
    """

    @abstractmethod
    def map_tool(self, tool: Tool) -> ToolMappingResult:
        """Process a single Tool and return an enriched or static mapping result."""
        pass

    @abstractmethod
    def map_tools(self, tools: list[Tool]) -> list[ToolMappingResult]:
        """Process a collection of tools."""
        pass

    @abstractmethod
    def resolve_ambiguity(
        self, intent: str, candidate_tools: list[Tool]
    ) -> tuple[Tool, float, str]:
        """Given a user intent and multiple candidate tools, select the best tool.

        Returns a tuple of (selected_tool, confidence_score, rationale).
        """
        pass
