from collections.abc import Callable
from typing import Any, TypeVar

from mcptoolforge.prompts.prompt import Prompt

F = TypeVar("F", bound=Callable[..., Any])


class PromptDecorator:
    """Decorator to register functions as prompts on a PromptRegistry."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Check if used as @prompt directly
        if len(args) == 1 and callable(args[0]) and not kwargs:
            func = args[0]
            prompt = Prompt(func)
            self._registry.register(prompt)
            return func

        # Used as @prompt(name=..., description=...)
        name: str | None = kwargs.get("name")
        description: str | None = kwargs.get("description")

        def decorator(func: F) -> F:
            prompt = Prompt(func, name=name, description=description)
            self._registry.register(prompt)
            return func

        return decorator
