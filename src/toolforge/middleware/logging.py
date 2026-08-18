import logging
from typing import Any

from toolforge.middleware.context import MiddlewareContext

logger = logging.getLogger("toolforge.middleware.logging")


async def logging_middleware(context: MiddlewareContext, next_callable: Any) -> Any:
    """Asynchronous built-in middleware for logging tool invocations to stderr."""
    logger.info(f"Calling tool '{context.tool_name}' with arguments: {context.arguments}")
    try:
        result = await next_callable()
        logger.info(f"Completed tool '{context.tool_name}' successfully.")
        return result
    except Exception as e:
        logger.error(f"Tool '{context.tool_name}' failed with error: {e}")
        raise


def sync_logging_middleware(context: MiddlewareContext, next_callable: Any) -> Any:
    """Synchronous built-in middleware for logging tool invocations to stderr."""
    logger.info(f"Calling tool '{context.tool_name}' with arguments: {context.arguments}")
    try:
        result = next_callable()
        logger.info(f"Completed tool '{context.tool_name}' successfully.")
        return result
    except Exception as e:
        logger.error(f"Tool '{context.tool_name}' failed with error: {e}")
        raise
