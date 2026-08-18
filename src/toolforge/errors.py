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
