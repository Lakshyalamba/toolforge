from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from toolforge.intelligence.dataset import MappingDataset, MappingExample
from toolforge.intelligence.errors import DSPyNotInstalledError, OptimizationError
from toolforge.intelligence.metrics import semantic_mapping_metric

try:
    import dspy
    from dspy.teleprompt import BootstrapFewShot

    _HAS_DSPY = True
except ImportError:
    dspy = None
    BootstrapFewShot = None  # type: ignore[assignment, misc]
    _HAS_DSPY = False

if TYPE_CHECKING:
    from toolforge.intelligence.mapper.dspy_mapper import DSPyToolMapper


class MapperOptimizer:
    """Offline optimization workflow using DSPy teleprompters (few-shot optimizers).

    Compiles ToolEnricherModule or DSPyToolMapper using verified examples and evaluation metrics.
    """

    def __init__(
        self,
        max_bootstrapped_demos: int = 2,
        max_labeled_demos: int = 2,
        metric: Callable[..., float] = semantic_mapping_metric,
    ) -> None:
        self.max_bootstrapped_demos = max_bootstrapped_demos
        self.max_labeled_demos = max_labeled_demos
        self.metric = metric

    def compile(
        self,
        mapper_or_module: Any,
        trainset: MappingDataset | list[MappingExample],
        valset: MappingDataset | list[MappingExample] | None = None,
    ) -> Any:
        """Compile the student module against the training dataset using BootstrapFewShot.

        Args:
            mapper_or_module: DSPyToolMapper instance or raw ToolEnricherModule.
            trainset: Dataset of known-correct mapping examples.
            valset: Optional validation dataset.

        Returns:
            A new compiled DSPyToolMapper (if DSPyToolMapper was provided) or compiled module.
        """
        if not _HAS_DSPY or dspy is None or BootstrapFewShot is None:
            raise DSPyNotInstalledError(
                "Optimization requires DSPy. Install via 'pip install \"mcptoolforge[dspy]\"'."
            )

        examples = trainset.examples if isinstance(trainset, MappingDataset) else trainset
        if not examples:
            raise OptimizationError("Optimization trainset cannot be empty.")

        dspy_trainset = [ex.to_dspy_example() for ex in examples]

        # Determine student module and source mapper
        source_mapper: DSPyToolMapper | None = None
        if hasattr(mapper_or_module, "_enricher"):
            source_mapper = mapper_or_module
            student = mapper_or_module._enricher
            if student is None:
                from toolforge.intelligence.modules import ToolEnricherModule

                student = ToolEnricherModule()
        else:
            student = mapper_or_module

        if not hasattr(student, "forward"):
            raise OptimizationError(
                f"Target module '{type(student).__name__}' is not a valid DSPy module."
            )

        teleprompter = BootstrapFewShot(
            metric=self.metric,
            max_bootstrapped_demos=self.max_bootstrapped_demos,
            max_labeled_demos=self.max_labeled_demos,
        )

        try:
            compiled_enricher = teleprompter.compile(student=student, trainset=dspy_trainset)
        except Exception as e:
            raise OptimizationError(f"DSPy teleprompter compilation failed: {e}") from e

        if source_mapper is not None:
            from toolforge.intelligence.mapper.dspy_mapper import DSPyToolMapper

            return DSPyToolMapper(
                fallback_mapper=source_mapper.fallback_mapper,
                confidence_threshold=source_mapper.confidence_threshold,
                strict=source_mapper.strict,
                enricher_module=compiled_enricher,
                disambiguator_module=source_mapper._disambiguator,
                compiled=True,
            )

        return compiled_enricher


def save_optimized_program(
    mapper_or_module: Any,
    output_path: str | Path,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Save a compiled DSPy program state and optional metadata to disk.

    Args:
        mapper_or_module: A DSPyToolMapper instance or DSPy Module.
        output_path: Destination path for the saved JSON weights/state.
        metadata: Optional dictionary with evaluation metrics or model details.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    module = getattr(mapper_or_module, "_enricher", mapper_or_module)
    if not hasattr(module, "save"):
        raise OptimizationError(
            f"Cannot save program: module {type(module).__name__} does not have a 'save' method."
        )

    try:
        module.save(str(path))
    except Exception as e:
        raise OptimizationError(f"Failed to save compiled program to '{path}': {e}") from e

    if metadata is not None:
        meta_path = path.with_suffix(".meta.json")
        try:
            meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        except Exception as e:
            raise OptimizationError(
                f"Failed to write program metadata to '{meta_path}': {e}"
            ) from e


def load_optimized_program(program_path: str | Path) -> Any:
    """Load a compiled DSPy program state from disk into a ToolEnricherModule.

    Args:
        program_path: Path to the serialized JSON program state.

    Returns:
        Loaded ToolEnricherModule instance.
    """
    if not _HAS_DSPY:
        raise DSPyNotInstalledError(
            "Loading a compiled program requires DSPy. "
            "Install via 'pip install \"mcptoolforge[dspy]\"'."
        )

    path = Path(program_path)
    if not path.exists():
        raise FileNotFoundError(f"Compiled DSPy program file not found: '{path}'")

    from toolforge.intelligence.modules import ToolEnricherModule

    module = ToolEnricherModule()
    try:
        module.load(str(path))
    except Exception as e:
        raise OptimizationError(f"Failed to load compiled program from '{path}': {e}") from e

    return module
