from mcptoolforge.errors import ToolAlreadyRegisteredError, ToolNotFoundError
from mcptoolforge.prompts.prompt import Prompt


class PromptRegistry:
    """Manages prompt storage, lookup, and deletion."""

    def __init__(self) -> None:
        self._prompts: dict[str, Prompt] = {}

    def register(self, prompt: Prompt) -> None:
        """Register a prompt in the registry."""
        if prompt.name in self._prompts:
            raise ToolAlreadyRegisteredError(
                f"Duplicate prompt name: '{prompt.name}' is already registered."
            )
        self._prompts[prompt.name] = prompt

    def get(self, name: str) -> Prompt:
        """Retrieve a prompt by name."""
        if name not in self._prompts:
            raise ToolNotFoundError(f"Prompt '{name}' is not registered.")
        return self._prompts[name]

    def remove(self, name: str) -> None:
        """Remove a prompt by name."""
        if name not in self._prompts:
            raise ToolNotFoundError(f"Prompt '{name}' is not registered and cannot be removed.")
        del self._prompts[name]

    def list(self) -> list[Prompt]:
        """Return a list of all registered prompts."""
        return list(self._prompts.values())

    def contains(self, name: str) -> bool:
        """Check if a prompt is registered by name."""
        return name in self._prompts
