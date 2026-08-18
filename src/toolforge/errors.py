class ToolForgeError(Exception):
    """Base exception for all ToolForge errors."""

    pass


class ToolRegistrationError(ToolForgeError):
    """Raised when registering a tool fails."""

    pass


class ToolAlreadyRegisteredError(ToolRegistrationError):
    """Raised when trying to register a tool that is already registered."""

    pass


class ToolNotFoundError(ToolForgeError):
    """Raised when a tool is looked up but not found."""

    pass


class ToolExecutionError(ToolForgeError):
    """Raised when executing a tool fails."""

    pass


class SchemaGenerationError(ToolForgeError):
    """Raised when generating schema for a tool fails."""

    pass


class ToolValidationError(ToolForgeError):
    """Raised when validating tool arguments fails."""

    pass


class ConfigurationError(ToolForgeError):
    """Base exception for all configuration and project loading errors."""

    pass


class ProjectNotFoundError(ConfigurationError):
    """Raised when pyproject.toml is missing or does not contain a ToolForge configuration."""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values fail validation checks."""

    pass


class EntrypointNotFoundError(ConfigurationError):
    """Raised when the specified entrypoint cannot be located."""

    pass


class MiddlewareError(ToolForgeError):
    """Raised when middleware logic fails or raises an error."""

    pass


class ResourceRegistrationError(ToolForgeError):
    """Raised when registering a resource fails."""

    pass


class ResourceAlreadyRegisteredError(ResourceRegistrationError):
    """Raised when a resource with the same URI is already registered."""

    pass


class ResourceNotFoundError(ToolForgeError):
    """Raised when a resource is looked up but not found."""

    pass


class ResourceExecutionError(ToolForgeError):
    """Raised when executing/reading a resource fails."""

    pass
