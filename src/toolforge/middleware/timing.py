import logging
import time
from typing import Any

from toolforge.middleware.context import MiddlewareContext

logger = logging.getLogger("toolforge.middleware.timing")


async def timing_middleware(context: MiddlewareContext, next_callable: Any) -> Any:
    """Asynchronous built-in middleware for measuring execution duration."""
    start = time.perf_counter()
    try:
        result = await next_callable()
        context.duration = time.perf_counter() - start
        logger.info(f"Tool '{context.tool_name}' execution took {context.duration:.4f} seconds.")
        return result
    except Exception as e:
        context.duration = time.perf_counter() - start
        context.error = e
        logger.error(f"Tool '{context.tool_name}' failed after {context.duration:.4f} seconds.")
        raise


def sync_timing_middleware(context: MiddlewareContext, next_callable: Any) -> Any:
    """Synchronous built-in middleware for measuring execution duration."""
    start = time.perf_counter()
    try:
        result = next_callable()
        context.duration = time.perf_counter() - start
        logger.info(f"Tool '{context.tool_name}' execution took {context.duration:.4f} seconds.")
        return result
    except Exception as e:
        context.duration = time.perf_counter() - start
        context.error = e
        logger.error(f"Tool '{context.tool_name}' failed after {context.duration:.4f} seconds.")
        raise
