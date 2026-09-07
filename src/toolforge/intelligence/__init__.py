from toolforge.config import DSPyConfig, DSPyOptimizationConfig
from toolforge.intelligence.agent import AgentResult, ToolForgeAgent
from toolforge.intelligence.benchmark import (
    BenchmarkComparison,
    BenchmarkMetrics,
    BenchmarkRunner,
    get_default_benchmark_dataset,
)
from toolforge.intelligence.dataset import MappingDataset, MappingExample
from toolforge.intelligence.errors import (
    DatasetValidationError,
    DSPyNotInstalledError,
    IntelligenceError,
    OptimizationError,
    ToolMappingError,
)
from toolforge.intelligence.evaluator import EvaluationDetail, EvaluationResult, MappingEvaluator
from toolforge.intelligence.mapper import (
    DSPyToolMapper,
    StaticToolMapper,
    ToolMapper,
)
from toolforge.intelligence.metrics import (
    category_match,
    domain_match,
    risk_match,
    semantic_mapping_metric,
    tool_selection_match,
)
from toolforge.intelligence.models import (
    ParameterSemantics,
    ToolMappingResult,
    ToolRiskLevel,
    ToolSemantics,
)
from toolforge.intelligence.optimizer import (
    MapperOptimizer,
    load_optimized_program,
    save_optimized_program,
)
from toolforge.intelligence.tools import (
    DSPyToolAdapter,
    ToolInvocationRecord,
    ToolTrace,
    to_dspy_tool,
    to_dspy_tools,
)


def is_dspy_available() -> bool:
    """Return True if dspy is installed and importable, False otherwise."""
    try:
        import dspy  # noqa: F401

        return True
    except ImportError:
        return False


__all__ = [
    "AgentResult",
    "BenchmarkComparison",
    "BenchmarkMetrics",
    "BenchmarkRunner",
    "DSPyConfig",
    "DSPyNotInstalledError",
    "DSPyOptimizationConfig",
    "DSPyToolAdapter",
    "DSPyToolMapper",
    "DatasetValidationError",
    "EvaluationDetail",
    "EvaluationResult",
    "IntelligenceError",
    "MapperOptimizer",
    "MappingDataset",
    "MappingEvaluator",
    "MappingExample",
    "OptimizationError",
    "ParameterSemantics",
    "StaticToolMapper",
    "ToolForgeAgent",
    "ToolInvocationRecord",
    "ToolMapper",
    "ToolMappingError",
    "ToolMappingResult",
    "ToolRiskLevel",
    "ToolSemantics",
    "ToolTrace",
    "category_match",
    "domain_match",
    "get_default_benchmark_dataset",
    "is_dspy_available",
    "load_optimized_program",
    "risk_match",
    "save_optimized_program",
    "semantic_mapping_metric",
    "to_dspy_tool",
    "to_dspy_tools",
    "tool_selection_match",
]
