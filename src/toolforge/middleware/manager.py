import inspect
from collections.abc import Callable
from typing import Any

from toolforge.errors import ConfigurationError
from toolforge.middleware.context import MiddlewareContext


def is_async_callable(fn: Any) -> bool:
    """Helper to check if a callable is asynchronous."""
    if inspect.iscoroutinefunction(fn):
        return True
    return bool(callable(fn) and inspect.iscoroutinefunction(fn.__call__))


def build_chain(
    middlewares: list[Callable], context: MiddlewareContext, final_call: Callable
) -> Callable:
    """Build a nested execution chain of middlewares.

    Validates sync/async compatibility: synchronous middleware cannot wrap
    asynchronous tools or middlewares.
    """
    # 1. Determine if each stage is async
    is_async_stage = []
    for mw in middlewares:
        is_async_stage.append(is_async_callable(mw))
    is_async_stage.append(is_async_callable(final_call))

    # 2. Check for invalid sync -> async transitions
    for i in range(len(middlewares)):
        if not is_async_stage[i] and any(is_async_stage[i + 1 :]):
            raise ConfigurationError(
                f"Synchronous middleware '{middlewares[i].__name__}' cannot be used "
                "because a subsequent middleware or tool in the pipeline is asynchronous."
            )

    # 3. Build the closures from the tail to the head
    current_next = final_call

    for i in reversed(range(len(middlewares))):
        mw = middlewares[i]
        is_mw_async = is_async_stage[i]

        if is_mw_async:
            # Wrap current_next in a coroutine function if it isn't one,
            # so next() behaves asynchronously
            wrapped_next = current_next
            if not is_async_callable(wrapped_next):

                async def async_wrapped(*args, _next=wrapped_next, **kwargs):
                    return _next(*args, **kwargs)

                wrapped_next = async_wrapped

            # Create the async wrapper closure
            async def async_next_step(m=mw, c=context, n=wrapped_next):
                return await m(c, n)

            current_next = async_next_step
        else:
            # Create the sync wrapper closure
            def sync_next_step(m=mw, c=context, n=current_next):
                return m(c, n)

            current_next = sync_next_step

    return current_next
