class MCPToolForgeError(Exception):
    """Base exception for all MCPToolForge errors."""

    pass


class ToolRegistrationError(MCPToolForgeError):
    """Raised when registering a tool fails."""

    pass


class ToolAlreadyRegisteredError(ToolRegistrationError):
    """Raised when trying to register a tool that is already registered."""

    pass


class ToolNotFoundError(MCPToolForgeError):
    """Raised when a tool is looked up but not found."""

    pass


class ToolExecutionError(MCPToolForgeError):
    """Raised when executing a tool fails."""

    pass


class SchemaGenerationError(MCPToolForgeError):
    """Raised when generating schema for a tool fails."""

    pass


class ToolValidationError(MCPToolForgeError):
    """Raised when validating tool arguments fails."""

    pass


class ConfigurationError(MCPToolForgeError):
    """Base exception for all configuration and project loading errors."""

    pass


class ProjectNotFoundError(ConfigurationError):
    """Raised when pyproject.toml is missing or does not contain a MCPToolForge configuration."""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values fail validation checks."""

    pass


class EntrypointNotFoundError(ConfigurationError):
    """Raised when the specified entrypoint cannot be located."""

    pass


class MiddlewareError(MCPToolForgeError):
    """Raised when middleware logic fails or raises an error."""

    pass


class ResourceRegistrationError(MCPToolForgeError):
    """Raised when registering a resource fails."""

    pass


class ResourceAlreadyRegisteredError(ResourceRegistrationError):
    """Raised when a resource with the same URI is already registered."""

    pass


class ResourceNotFoundError(MCPToolForgeError):
    """Raised when a resource is looked up but not found."""

    pass


class ResourceExecutionError(MCPToolForgeError):
    """Raised when executing/reading a resource fails."""

    pass
