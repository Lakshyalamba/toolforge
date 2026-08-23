from dataclasses import dataclass

from mcptoolforge.errors import InvalidConfigurationError


@dataclass
class MCPToolForgeConfig:
    """Typed, validated representation of MCPToolForge project configuration."""

    name: str
    entrypoint: str = "server.py"
    transport: str = "stdio"

    def __post_init__(self) -> None:
        # Validate name
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidConfigurationError(
                "MCPToolForge configuration 'name' must be a non-empty string."
            )
        self.name = self.name.strip()

        # Validate entrypoint
        if not isinstance(self.entrypoint, str) or not self.entrypoint.strip():
            raise InvalidConfigurationError(
                "MCPToolForge configuration 'entrypoint' must be a non-empty string."
            )
        self.entrypoint = self.entrypoint.strip()

        if not self.entrypoint.endswith(".py"):
            raise InvalidConfigurationError(
                f"MCPToolForge entrypoint '{self.entrypoint}' is not a Python file."
            )

        # Validate transport
        if not isinstance(self.transport, str) or not self.transport.strip():
            raise InvalidConfigurationError(
                "MCPToolForge configuration 'transport' must be a non-empty string."
            )
        self.transport = self.transport.strip()

        if self.transport != "stdio":
            raise InvalidConfigurationError(
                f"Unsupported transport '{self.transport}' for MCPToolForge server. "
                "Only 'stdio' is currently supported."
            )
