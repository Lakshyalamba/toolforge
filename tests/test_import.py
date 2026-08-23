def test_import_server() -> None:
    """Verify that MCPServer and base exceptions can be imported."""
    from mcptoolforge import (
        MCPServer,
        MCPToolForgeError,
        SchemaGenerationError,
        ToolExecutionError,
        ToolRegistrationError,
    )

    assert MCPServer is not None
    assert MCPToolForgeError is not None
    assert ToolRegistrationError is not None
    assert ToolExecutionError is not None
    assert SchemaGenerationError is not None
