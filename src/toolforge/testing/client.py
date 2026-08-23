import asyncio
import base64
import inspect
import json
import time
from typing import Any

from toolforge.errors import (
    ResourceExecutionError,
    ResourceNotFoundError,
    ToolExecutionError,
    ToolForgeError,
    ToolNotFoundError,
    ToolValidationError,
)


class ToolForgeTestingError(ToolForgeError):
    """Exception raised for general ToolForge test client errors."""

    pass


class ResourceReadResult:
    """Convenient result container for reading resources in tests."""

    def __init__(
        self,
        uri: str,
        text: str | None = None,
        blob: str | None = None,
        mime_type: str | None = None,
    ):
        self.uri = uri
        self.text = text
        self.blob = blob
        self.mime_type = mime_type

    @property
    def is_blob(self) -> bool:
        return self.blob is not None

    def __repr__(self) -> str:
        return (
            f"ResourceReadResult(uri={self.uri!r}, text={self.text!r}, "
            f"blob={self.blob!r}, mime_type={self.mime_type!r})"
        )


class PromptMessageResult:
    """Represents a message result of a prompt retrieval in tests."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def __repr__(self) -> str:
        return f"PromptMessageResult(role={self.role!r}, content={self.content!r})"


class PromptGetResult:
    """Convenient result container for retrieved prompts in tests."""

    def __init__(self, messages: list[PromptMessageResult], description: str | None = None):
        self.messages = messages
        self.description = description

    def __repr__(self) -> str:
        return f"PromptGetResult(messages={self.messages!r}, description={self.description!r})"


class MCPTestClient:
    """First-class in-process testing client for ToolForge MCPServers."""

    def __init__(self, server: Any) -> None:
        self._server = server

    def _run_sync(self, coro_fn: Any) -> Any:
        import anyio

        try:
            asyncio.get_running_loop()
            # If there's already a running loop, running anyio.run raises a RuntimeError.
            # We must await or warn. To be safe:
            raise ToolForgeTestingError(
                "Cannot execute synchronous test method inside a running event loop. "
                "Use the async version (e.g. `await client.call_tool_async(...)`) instead."
            )
        except RuntimeError:
            pass

        return anyio.run(coro_fn)

    # --- Startup/Shutdown Lifecycle ---

    def start(self) -> None:
        """Run startup hooks synchronously."""
        for hook in self._server.startup_hooks:
            if inspect.iscoroutinefunction(hook):
                self._run_sync(lambda h=hook: h())
            else:
                hook()

    def stop(self) -> None:
        """Run shutdown hooks synchronously."""
        for hook in self._server.shutdown_hooks:
            if inspect.iscoroutinefunction(hook):
                self._run_sync(lambda h=hook: h())
            else:
                hook()

    async def start_async(self) -> None:
        """Run startup hooks asynchronously."""
        for hook in self._server.startup_hooks:
            if inspect.iscoroutinefunction(hook):
                await hook()
            else:
                hook()

    async def stop_async(self) -> None:
        """Run shutdown hooks asynchronously."""
        for hook in self._server.shutdown_hooks:
            if inspect.iscoroutinefunction(hook):
                await hook()
            else:
                hook()

    def __enter__(self) -> "MCPTestClient":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    async def __aenter__(self) -> "MCPTestClient":
        await self.start_async()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop_async()

    # --- Tools ---

    def list_tools(self) -> list[Any]:
        """List registered tools from the MCPServer."""
        return self._server.list_tools()

    async def call_tool_async(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Execute a tool asynchronously through the server's validation and middleware pipeline."""
        if not self._server.has_tool(name):
            raise ToolNotFoundError(f"Tool '{name}' is not registered.")

        tf_tool = self._server.get_tool(name)
        raw_args = arguments or {}

        if self._server.middlewares:
            from toolforge.middleware.context import MiddlewareContext
            from toolforge.middleware.manager import build_chain, is_async_callable

            context = MiddlewareContext(
                tool_name=tf_tool.name,
                tool=tf_tool,
                arguments=raw_args,
                server=self._server,
            )

            called_next = False

            if inspect.iscoroutinefunction(tf_tool.fn):

                async def final_call() -> Any:
                    nonlocal called_next
                    called_next = True
                    from toolforge.validation import validate_tool_arguments

                    validated_args = validate_tool_arguments(tf_tool, context.arguments)
                    try:
                        return await tf_tool.fn(**validated_args)
                    except Exception as inner_e:
                        if not isinstance(inner_e, (ToolValidationError, ToolExecutionError)):
                            raise ToolExecutionError(
                                f"Error executing tool '{tf_tool.name}': {inner_e}"
                            ) from inner_e
                        raise

            else:

                def final_call() -> Any:
                    nonlocal called_next
                    called_next = True
                    from toolforge.validation import validate_tool_arguments

                    validated_args = validate_tool_arguments(tf_tool, context.arguments)
                    try:
                        return tf_tool.fn(**validated_args)
                    except Exception as inner_e:
                        if not isinstance(inner_e, (ToolValidationError, ToolExecutionError)):
                            raise ToolExecutionError(
                                f"Error executing tool '{tf_tool.name}': {inner_e}"
                            ) from inner_e
                        raise

            start_time = time.perf_counter()
            chain_callable = build_chain(self._server.middlewares, context, final_call)

            if inspect.iscoroutinefunction(chain_callable) or is_async_callable(chain_callable):
                result = await chain_callable()
            else:
                result = chain_callable()

            context.duration = time.perf_counter() - start_time
            return result
        else:
            from toolforge.execution import execute_tool

            return await execute_tool(tf_tool, raw_args)

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Execute a tool synchronously through the server's validation and middleware pipeline."""
        return self._run_sync(lambda: self.call_tool_async(name, arguments))

    # --- Resources ---

    def list_resources(self) -> list[Any]:
        """List registered resources from the MCPServer."""
        return self._server.list_resources()

    async def read_resource_async(self, uri: str) -> ResourceReadResult:
        """Read a resource asynchronously through the server's resource handler."""
        if not self._server.has_resource(uri):
            raise ResourceNotFoundError(f"Resource '{uri}' is not registered.")

        tf_resource = self._server.get_resource(uri)

        try:
            if inspect.iscoroutinefunction(tf_resource.fn):
                raw_result = await tf_resource.fn()
            else:
                raw_result = tf_resource.fn()
        except Exception as e:
            raise ResourceExecutionError(f"Resource execution failed: {e}") from e

        mime_type = tf_resource.mime_type
        if isinstance(raw_result, (dict, list)):
            if mime_type is None:
                mime_type = "application/json"
            try:
                serialized_text = json.dumps(raw_result)
            except Exception as json_e:
                raise ResourceExecutionError(
                    f"Failed to serialize resource content to JSON: {json_e}"
                ) from json_e
            return ResourceReadResult(
                uri=tf_resource.uri,
                text=serialized_text,
                mime_type=mime_type,
            )
        elif isinstance(raw_result, str):
            return ResourceReadResult(
                uri=tf_resource.uri,
                text=raw_result,
                mime_type=mime_type,
            )
        elif isinstance(raw_result, bytes):
            b64_str = base64.b64encode(raw_result).decode("utf-8")
            return ResourceReadResult(
                uri=tf_resource.uri,
                blob=b64_str,
                mime_type=mime_type,
            )
        else:
            raise ResourceExecutionError(
                f"Unsupported resource return type: {type(raw_result).__name__}"
            )

    def read_resource(self, uri: str) -> ResourceReadResult:
        """Read a resource synchronously through the server's resource handler."""
        return self._run_sync(lambda: self.read_resource_async(uri))

    # --- Prompts ---

    def list_prompts(self) -> list[Any]:
        """List registered prompts from the MCPServer."""
        return self._server.list_prompts()

    async def get_prompt_async(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> PromptGetResult:
        """Retrieve a prompt template asynchronously with validation and mapping."""
        if not self._server.has_prompt(name):
            raise ToolNotFoundError(f"Prompt '{name}' is not registered.")

        tf_prompt = self._server.get_prompt(name)
        raw_args = arguments or {}

        from toolforge.validation import validate_prompt_arguments

        try:
            validated_args = validate_prompt_arguments(tf_prompt, raw_args)
        except Exception as val_e:
            raise ToolValidationError(f"Prompt argument validation failed: {val_e}") from val_e

        try:
            if inspect.iscoroutinefunction(tf_prompt.fn):
                raw_result = await tf_prompt.fn(**validated_args)
            else:
                raw_result = tf_prompt.fn(**validated_args)
        except Exception as e:
            raise ToolExecutionError(f"Prompt execution failed: {e}") from e

        messages = []

        def make_message(text_val: str, role_val: str = "user") -> PromptMessageResult:
            if role_val not in ("user", "assistant"):
                raise ToolExecutionError(
                    f"Role '{role_val}' is not supported. Only 'user' or 'assistant' are allowed."
                )
            return PromptMessageResult(role=role_val, content=text_val)

        if isinstance(raw_result, str):
            messages.append(make_message(raw_result))
        elif isinstance(raw_result, dict):
            role = raw_result.get("role", "user")
            content = raw_result.get("content", "")
            if not isinstance(content, str):
                tname = type(content).__name__
                raise ToolExecutionError(f"Prompt dict content must be a string, received {tname}")
            messages.append(make_message(content, role))
        elif isinstance(raw_result, list):
            for item in raw_result:
                if isinstance(item, str):
                    messages.append(make_message(item))
                elif isinstance(item, dict):
                    role = item.get("role", "user")
                    content = item.get("content", "")
                    if not isinstance(content, str):
                        tname = type(content).__name__
                        raise ToolExecutionError(
                            f"Prompt dict content must be a string, received {tname}"
                        )
                    messages.append(make_message(content, role))
                elif hasattr(item, "role") and hasattr(item, "content"):
                    content_text = item.content
                    if hasattr(content_text, "text"):
                        content_text = content_text.text
                    messages.append(make_message(str(content_text), str(item.role)))
                else:
                    tname = type(item).__name__
                    raise ToolExecutionError(
                        f"Unsupported item type in prompt result list: {tname}"
                    )
        elif hasattr(raw_result, "role") and hasattr(raw_result, "content"):
            content_text = raw_result.content
            if hasattr(content_text, "text"):
                content_text = content_text.text
            messages.append(make_message(str(content_text), str(raw_result.role)))
        else:
            raise ToolExecutionError(f"Unsupported prompt return type: {type(raw_result).__name__}")

        return PromptGetResult(messages=messages, description=tf_prompt.description)

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> PromptGetResult:
        """Retrieve a prompt template synchronously with validation and mapping."""
        return self._run_sync(lambda: self.get_prompt_async(name, arguments))
