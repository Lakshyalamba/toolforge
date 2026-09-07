from toolforge.errors import ToolForgeError


class IntelligenceError(ToolForgeError):
    """Base exception for all intelligence and semantic mapping errors."""

    pass


class DSPyNotInstalledError(IntelligenceError):
    """Raised when DSPy functionality is explicitly requested but 'dspy' is not installed."""

    pass


class ToolMappingError(IntelligenceError):
    """Raised when tool mapping or enrichment fails and fallback is disabled."""

    pass


class DatasetValidationError(IntelligenceError):
    """Raised when an evaluation or optimization dataset is invalid or malformed."""

    pass


class OptimizationError(IntelligenceError):
    """Raised when optimizer compilation or artifact serialization fails."""

    pass
