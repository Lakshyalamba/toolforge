import concurrent.futures
import json
import logging
from typing import Any

from toolforge.intelligence.errors import DSPyNotInstalledError, ToolMappingError
from toolforge.intelligence.mapper.base import ToolMapper
from toolforge.intelligence.mapper.static import StaticToolMapper
from toolforge.intelligence.models import (
    ToolMappingResult,
    ToolRiskLevel,
    ToolSemantics,
)
from toolforge.registry import Tool

logger = logging.getLogger("toolforge.intelligence")


class DSPyToolMapper(ToolMapper):
    """AI-powered semantic tool mapper leveraging DSPy programs.

    Enriches tools with deep semantic understanding, operational risk classification,
    and LLM-optimized docstrings, with configurable, automatic fallback to StaticToolMapper.
    """

    def __init__(
        self,
        fallback_mapper: ToolMapper | None = None,
        confidence_threshold: float = 0.6,
        strict: bool = False,
        enricher_module: Any | None = None,
        disambiguator_module: Any | None = None,
        compiled: bool = False,
        enable_cache: bool = True,
    ) -> None:
        self.fallback_mapper = fallback_mapper or StaticToolMapper()
        self.confidence_threshold = confidence_threshold
        self.strict = strict
        self.compiled = compiled
        self.enable_cache = enable_cache
        self._cache: dict[str, ToolMappingResult] = {}

        self._enricher = enricher_module
        self._disambiguator = disambiguator_module

        self._init_modules()

    def _init_modules(self) -> None:
        """Initialize DSPy modules if available and not already provided."""
        if self._enricher is not None and self._disambiguator is not None:
            return

        try:
            import dspy  # noqa: F401

            from toolforge.intelligence.modules import (
                ToolDisambiguatorModule,
                ToolEnricherModule,
            )

            if self._enricher is None:
                self._enricher = ToolEnricherModule()
            if self._disambiguator is None:
                self._disambiguator = ToolDisambiguatorModule()
        except (ImportError, DSPyNotInstalledError):
            if self.strict:
                raise DSPyNotInstalledError(
                    "DSPy is not installed. Install it via 'pip install \"mcptoolforge[dspy]\"'."
                ) from None
            self._enricher = None
            self._disambiguator = None

    @property
    def is_dspy_ready(self) -> bool:
        """Check whether DSPy modules are initialized and ready."""
        return self._enricher is not None and self._disambiguator is not None

    def _get_cache_key(self, tool: Tool) -> str:
        """Generate a deterministic cache key for a tool based on its name, doc, and schema."""
        try:
            schema_repr = json.dumps(tool.input_schema, sort_keys=True)
        except (TypeError, ValueError):
            schema_repr = str(tool.input_schema)
        return f"{tool.name}::{tool.description}::{schema_repr}"

    def clear_cache(self) -> None:
        """Clear the in-memory tool mapping cache."""
        self._cache.clear()

    def map_tool(self, tool: Tool) -> ToolMappingResult:
        """Map and enrich a Tool using DSPy, falling back to static mapping if needed."""
        cache_key = self._get_cache_key(tool) if self.enable_cache else None
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key]

        if not self.is_dspy_ready or self._enricher is None:
            if self.strict:
                raise DSPyNotInstalledError(
                    "DSPy is not installed or initialized, and strict=True is set."
                )
            result = self.fallback_mapper.map_tool(tool)
            if cache_key is not None:
                self._cache[cache_key] = result
            return result

        try:
            prediction = self._enricher(
                tool_name=tool.name,
                docstring=tool.description,
                input_schema=tool.input_schema,
            )

            raw_confidence = getattr(prediction, "confidence", 1.0)
            try:
                confidence = float(raw_confidence)
            except (ValueError, TypeError):
                confidence = 1.0

            if confidence < self.confidence_threshold:
                msg = (
                    f"Tool '{tool.name}' enrichment confidence {confidence:.2f} "
                    f"is below threshold {self.confidence_threshold:.2f}."
                )
                if self.strict:
                    raise ToolMappingError(msg)
                logger.warning(f"{msg} Falling back to static mapper.")
                result = self.fallback_mapper.map_tool(tool)
                if cache_key is not None:
                    self._cache[cache_key] = result
                return result

            raw_risk = getattr(prediction, "risk_level", "unknown").lower()
            try:
                risk_level = ToolRiskLevel(raw_risk)
            except ValueError:
                risk_level = ToolRiskLevel.UNKNOWN

            improved_desc = getattr(prediction, "improved_description", "").strip()
            effective_desc = improved_desc if improved_desc else tool.description

            semantics = ToolSemantics(
                domain=getattr(prediction, "domain", "general"),
                category=getattr(prediction, "category", "utility"),
                primary_intent=getattr(prediction, "primary_intent", ""),
                risk_level=risk_level,
                improved_description=improved_desc,
                negative_examples=getattr(prediction, "negative_examples", []),
                confidence_score=confidence,
            )

            result = ToolMappingResult(
                name=tool.name,
                original_description=tool.description,
                effective_description=effective_desc,
                input_schema=tool.input_schema,
                semantics=semantics,
                is_enriched=True,
                confidence=confidence,
                mapping_source="dspy_compiled" if self.compiled else "dspy",
            )
            if cache_key is not None:
                self._cache[cache_key] = result
            return result

        except Exception as e:
            if self.strict:
                raise ToolMappingError(f"Failed to map tool '{tool.name}': {e}") from e
            logger.warning(f"DSPy mapping failed for tool '{tool.name}': {e}. Falling back.")
            result = self.fallback_mapper.map_tool(tool)
            if cache_key is not None:
                self._cache[cache_key] = result
            return result

    def map_tools(self, tools: list[Tool]) -> list[ToolMappingResult]:
        """Map a collection of tools, using parallel execution for multiple tools."""
        if len(tools) <= 1:
            return [self.map_tool(t) for t in tools]

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(tools))) as executor:
            return list(executor.map(self.map_tool, tools))

    def resolve_ambiguity(
        self, intent: str, candidate_tools: list[Tool]
    ) -> tuple[Tool, float, str]:
        """Disambiguate tool selection using DSPy semantic reasoning."""
        if not candidate_tools:
            raise ValueError("Candidate tools list cannot be empty.")

        if not self.is_dspy_ready or self._disambiguator is None:
            if self.strict:
                raise DSPyNotInstalledError(
                    "DSPy is not installed or initialized, and strict=True is set."
                )
            return self.fallback_mapper.resolve_ambiguity(intent, candidate_tools)

        try:
            tool_descriptions = [
                f"Name: {t.name}\nDescription: {t.description}\nSchema: {t.input_schema}"
                for t in candidate_tools
            ]

            prediction = self._disambiguator(
                intent=intent,
                candidate_tools=tool_descriptions,
            )

            selected_name = getattr(prediction, "selected_tool", "").strip()
            confidence = float(getattr(prediction, "confidence", 0.7))
            rationale = getattr(prediction, "rationale", "")

            # Match against candidate tools
            for t in candidate_tools:
                if t.name.lower() == selected_name.lower():
                    if confidence >= self.confidence_threshold:
                        return t, confidence, rationale
                    break

            # If not matched or below confidence threshold
            if self.strict:
                raise ToolMappingError(
                    f"Ambiguity resolution failed to match a valid candidate with sufficient "
                    f"confidence (confidence={confidence:.2f}, selected='{selected_name}')."
                )

            return self.fallback_mapper.resolve_ambiguity(intent, candidate_tools)

        except Exception as e:
            if self.strict:
                raise ToolMappingError(f"Error resolving tool ambiguity: {e}") from e
            logger.warning(f"DSPy ambiguity resolution failed: {e}. Using fallback.")
            return self.fallback_mapper.resolve_ambiguity(intent, candidate_tools)

    @classmethod
    def from_compiled(
        cls,
        program_path: str,
        fallback_mapper: ToolMapper | None = None,
        confidence_threshold: float = 0.6,
        strict: bool = False,
        enable_cache: bool = True,
    ) -> "DSPyToolMapper":
        """Instantiate a DSPyToolMapper from a compiled program file saved on disk."""
        from toolforge.intelligence.optimizer import load_optimized_program

        loaded_enricher = load_optimized_program(program_path)
        return cls(
            fallback_mapper=fallback_mapper,
            confidence_threshold=confidence_threshold,
            strict=strict,
            enricher_module=loaded_enricher,
            compiled=True,
            enable_cache=enable_cache,
        )

    @classmethod
    def from_config(
        cls,
        config: Any,
        fallback_mapper: ToolMapper | None = None,
        strict: bool = False,
        enable_cache: bool = True,
    ) -> "DSPyToolMapper":
        """Instantiate a DSPyToolMapper from a DSPyConfig object."""
        if getattr(config, "compiled_program_path", None):
            try:
                return cls.from_compiled(
                    config.compiled_program_path,
                    fallback_mapper=fallback_mapper,
                    confidence_threshold=getattr(config, "confidence_threshold", 0.6),
                    strict=strict,
                    enable_cache=enable_cache,
                )
            except Exception as e:
                if strict:
                    raise
                logger.warning(
                    f"Failed to load compiled program from '{config.compiled_program_path}': {e}. "
                    "Creating default DSPyToolMapper."
                )

        return cls(
            fallback_mapper=fallback_mapper,
            confidence_threshold=getattr(config, "confidence_threshold", 0.6),
            strict=strict,
            enable_cache=enable_cache,
        )
