def test_import_server() -> None:
    """Verify that MCPServer and base exceptions can be imported."""
    from toolforge import (
        MCPServer,
        SchemaGenerationError,
        ToolExecutionError,
        ToolForgeError,
        ToolRegistrationError,
    )

    assert MCPServer is not None
    assert ToolForgeError is not None
    assert ToolRegistrationError is not None
    assert ToolExecutionError is not None
    assert SchemaGenerationError is not None
