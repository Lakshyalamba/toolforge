from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from toolforge.errors import InvalidConfigurationError

if TYPE_CHECKING:
    from toolforge.intelligence.mapper.base import ToolMapper


@dataclass
class DSPyOptimizationConfig:
    """Configuration for offline prompt and pipeline optimization using DSPy teleprompters.

    Attributes:
        enabled: Whether prompt optimization is enabled for this project (default: False).
        cache_dir: Directory path used to store cached exemplars and compilation artifacts
                   (default: '.toolforge/intelligence').
    """

    enabled: bool = False
    cache_dir: str = ".toolforge/intelligence"
    max_bootstrapped_demos: int = 2
    max_labeled_demos: int = 2
    metric_threshold: float = 0.7

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.optimization.enabled' must be a boolean."
            )

        if not isinstance(self.cache_dir, str) or not self.cache_dir.strip():
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.optimization.cache_dir' must be a non-empty string."
            )
        self.cache_dir = self.cache_dir.strip()

        if (
            isinstance(self.max_bootstrapped_demos, bool)
            or not isinstance(self.max_bootstrapped_demos, int)
            or self.max_bootstrapped_demos < 0
        ):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.optimization.max_bootstrapped_demos' "
                "must be a non-negative integer."
            )

        if (
            isinstance(self.max_labeled_demos, bool)
            or not isinstance(self.max_labeled_demos, int)
            or self.max_labeled_demos < 0
        ):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.optimization.max_labeled_demos' "
                "must be a non-negative integer."
            )

        if (
            isinstance(self.metric_threshold, bool)
            or not isinstance(self.metric_threshold, (int, float))
            or not 0.0 <= float(self.metric_threshold) <= 1.0
        ):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.optimization.metric_threshold' "
                "must be a number between 0.0 and 1.0."
            )
        self.metric_threshold = float(self.metric_threshold)


@dataclass
class DSPyConfig:
    """Configuration for optional DSPy intelligence and semantic tool mapping layer.

    Attributes:
        enabled: Whether the DSPy intelligence layer is active (default: False).
        model: Provider and model identifier passed to the Language Model
               (e.g. 'openai/gpt-4o-mini', 'anthropic/claude-3-5-haiku').
        temperature: Sampling temperature for the Language Model between 0.0 and 2.0 (default: 0.0).
        confidence_threshold: Minimum confidence score required to accept AI enrichment before
                              falling back to static metadata, between 0.0 and 1.0 (default: 0.6).
        compiled_program_path: Optional filesystem path to pre-compiled DSPy program
                               weights or prompts.
        optimization: Settings for offline prompt teleprompters and optimizers.
    """

    enabled: bool = False
    model: str | None = None
    temperature: float = 0.0
    confidence_threshold: float = 0.6
    compiled_program_path: str | None = None
    optimization: DSPyOptimizationConfig = field(default_factory=DSPyOptimizationConfig)

    def __post_init__(self) -> None:
        # 1. Validate enabled
        if not isinstance(self.enabled, bool):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.enabled' must be a boolean."
            )

        # 2. Validate model
        if self.model is not None:
            if not isinstance(self.model, str) or not self.model.strip():
                raise InvalidConfigurationError(
                    "ToolForge configuration 'dspy.model' must be a non-empty string."
                )
            self.model = self.model.strip()

        # 3. Validate temperature (reject bools since bool is a subclass of int)
        if isinstance(self.temperature, bool) or not isinstance(self.temperature, (int, float)):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.temperature' must be a number."
            )
        if not 0.0 <= float(self.temperature) <= 2.0:
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.temperature' must be between 0.0 and 2.0."
            )
        self.temperature = float(self.temperature)

        # 4. Validate confidence_threshold
        if isinstance(self.confidence_threshold, bool) or not isinstance(
            self.confidence_threshold, (int, float)
        ):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.confidence_threshold' must be a number."
            )
        if not 0.0 <= float(self.confidence_threshold) <= 1.0:
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.confidence_threshold' must be between 0.0 and 1.0."
            )
        self.confidence_threshold = float(self.confidence_threshold)

        # 5. Validate compiled_program_path
        if self.compiled_program_path is not None:
            if (
                not isinstance(self.compiled_program_path, str)
                or not self.compiled_program_path.strip()
            ):
                raise InvalidConfigurationError(
                    "ToolForge configuration 'dspy.compiled_program_path' "
                    "must be a non-empty string."
                )
            self.compiled_program_path = self.compiled_program_path.strip()

        # 6. Validate optimization sub-config
        if isinstance(self.optimization, dict):
            self.optimization = DSPyOptimizationConfig(**self.optimization)
        elif not isinstance(self.optimization, DSPyOptimizationConfig):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy.optimization' must be a table/dictionary "
                "or DSPyOptimizationConfig instance."
            )

    def configure_lm(self) -> None:
        """Configure global DSPy settings from this configuration if DSPy is enabled."""
        if not self.enabled:
            return

        try:
            import dspy
        except ImportError as e:
            from toolforge.intelligence.errors import DSPyNotInstalledError

            raise DSPyNotInstalledError(
                "DSPy is enabled in configuration, but 'dspy' is not installed. "
                "Install it via 'pip install \"mcptoolforge[dspy]\"'."
            ) from e

        if self.model:
            lm = dspy.LM(self.model, temperature=self.temperature)
            dspy.settings.configure(lm=lm)


@dataclass
class ToolForgeConfig:
    """Typed, validated representation of ToolForge project configuration."""

    name: str
    entrypoint: str = "server.py"
    transport: str = "stdio"
    dspy: DSPyConfig = field(default_factory=DSPyConfig)

    def __post_init__(self) -> None:
        # Validate name
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidConfigurationError(
                "ToolForge configuration 'name' must be a non-empty string."
            )
        self.name = self.name.strip()

        # Validate entrypoint
        if not isinstance(self.entrypoint, str) or not self.entrypoint.strip():
            raise InvalidConfigurationError(
                "ToolForge configuration 'entrypoint' must be a non-empty string."
            )
        self.entrypoint = self.entrypoint.strip()

        if not self.entrypoint.endswith(".py"):
            raise InvalidConfigurationError(
                f"ToolForge entrypoint '{self.entrypoint}' is not a Python file."
            )

        # Validate transport
        if not isinstance(self.transport, str) or not self.transport.strip():
            raise InvalidConfigurationError(
                "ToolForge configuration 'transport' must be a non-empty string."
            )
        self.transport = self.transport.strip()

        if self.transport != "stdio":
            raise InvalidConfigurationError(
                f"Unsupported transport '{self.transport}' for ToolForge server. "
                "Only 'stdio' is currently supported."
            )

        # Validate dspy configuration
        if isinstance(self.dspy, dict):
            self.dspy = DSPyConfig(**self.dspy)
        elif not isinstance(self.dspy, DSPyConfig):
            raise InvalidConfigurationError(
                "ToolForge configuration 'dspy' must be a table/dictionary or DSPyConfig instance."
            )

    def create_mapper(self) -> "ToolMapper":
        """Instantiate the appropriate ToolMapper according to the dspy configuration."""
        if not self.dspy.enabled:
            from toolforge.intelligence.mapper.static import StaticToolMapper

            return StaticToolMapper()

        from toolforge.intelligence.mapper.dspy_mapper import DSPyToolMapper

        return DSPyToolMapper.from_config(self.dspy)
