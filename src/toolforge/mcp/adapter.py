import logging
from typing import Any

import mcp.types as t
from mcp.server.context import ServerRequestContext
from mcp.shared.exceptions import MCPError

from toolforge.errors import (
    ConfigurationError,
    MiddlewareError,
    ResourceNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from toolforge.execution import execute_tool
from toolforge.registry import ToolRegistry

logger = logging.getLogger("toolforge.mcp")


class MCPAdapter:
    """Adapts ToolForge ToolRegistry and tools to the MCP protocol server."""

    def __init__(
        self,
        registry: ToolRegistry,
        server: Any = None,
        resource_registry: Any = None,
        prompt_registry: Any = None,
    ) -> None:
        self.registry = registry
        self.server = server
        self.resource_registry = resource_registry or (server.resource_registry if server else None)
        self.prompt_registry = prompt_registry or (server.prompt_registry if server else None)

    async def handle_list_tools(
        self,
        ctx: ServerRequestContext[Any],
        params: t.PaginatedRequestParams | None,
    ) -> t.ListToolsResult:
        """Map registered ToolForge tools to MCP Tool representations."""
        mcp_tools = []
        for tf_tool in self.registry.list():
            mcp_tool = t.Tool(
                name=tf_tool.name,
                description=tf_tool.description,
                input_schema=tf_tool.input_schema,
            )
            mcp_tools.append(mcp_tool)
        return t.ListToolsResult(tools=mcp_tools)

    async def handle_call_tool(
        self,
        ctx: ServerRequestContext[Any],
        params: t.CallToolRequestParams,
    ) -> t.CallToolResult:
        """Execute the requested tool and translate results/errors to MCP format."""
        try:
            # 1. Locate the tool
            try:
                tf_tool = self.registry.get(params.name)
            except ToolNotFoundError as e:
                raise MCPError(code=-32601, message=str(e)) from e

            # 2. Extract arguments
            arguments = params.arguments or {}

            # 3. Execute the tool (wrapping with middlewares if configured)
            try:
                if self.server and self.server.middlewares:
                    import inspect
                    import time

                    from toolforge.middleware.context import MiddlewareContext
                    from toolforge.middleware.manager import build_chain, is_async_callable

                    context = MiddlewareContext(
                        tool_name=tf_tool.name,
                        tool=tf_tool,
                        arguments=arguments,
                        server=self.server,
                    )

                    called_next = False

                    if inspect.iscoroutinefunction(tf_tool.fn):

                        async def async_final_call() -> Any:
                            nonlocal called_next
                            called_next = True
                            from toolforge.validation import validate_tool_arguments

                            validated_args = validate_tool_arguments(tf_tool, context.arguments)

                            try:
                                return await tf_tool.fn(**validated_args)
                            except Exception as inner_e:
                                if not isinstance(
                                    inner_e, (ToolValidationError, ToolExecutionError)
                                ):
                                    raise ToolExecutionError(
                                        f"Error executing tool '{tf_tool.name}': {inner_e}"
                                    ) from inner_e
                                raise

                        target_final_call = async_final_call
                    else:

                        def sync_final_call() -> Any:
                            nonlocal called_next
                            called_next = True
                            from toolforge.validation import validate_tool_arguments

                            validated_args = validate_tool_arguments(tf_tool, context.arguments)

                            try:
                                return tf_tool.fn(**validated_args)
                            except Exception as inner_e:
                                if not isinstance(
                                    inner_e, (ToolValidationError, ToolExecutionError)
                                ):
                                    raise ToolExecutionError(
                                        f"Error executing tool '{tf_tool.name}': {inner_e}"
                                    ) from inner_e
                                raise

                        target_final_call = sync_final_call

                    start_time = time.perf_counter()
                    chain_callable = build_chain(
                        self.server.middlewares, context, target_final_call
                    )

                    try:
                        if inspect.iscoroutinefunction(chain_callable) or is_async_callable(
                            chain_callable
                        ):
                            result = await chain_callable()
                        else:
                            result = chain_callable()
                        context.duration = time.perf_counter() - start_time
                    except Exception as e:
                        context.duration = time.perf_counter() - start_time
                        context.error = e
                        if called_next and isinstance(e, (ToolValidationError, ToolExecutionError)):
                            raise
                        else:
                            raise MiddlewareError(f"Middleware failed during execution: {e}") from e
                else:
                    result = await execute_tool(tf_tool, arguments)

            except ToolValidationError as e:
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=str(e))],
                    is_error=True,
                )
            except (ToolExecutionError, MiddlewareError, ConfigurationError) as e:
                logger.error(f"Execution failed for tool '{params.name}': {e}", exc_info=True)
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=str(e))],
                    is_error=True,
                )

            # 4. Map return result to CallToolResult
            if isinstance(result, dict):
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=str(result))],
                    structured_content=result,
                    is_error=False,
                )
            else:
                text_value = result if isinstance(result, str) else str(result)
                return t.CallToolResult(
                    content=[t.TextContent(type="text", text=text_value)],
                    is_error=False,
                )

        except MCPError:
            raise
        except Exception as e:
            logger.critical(f"Internal ToolForge error in call_tool: {e}", exc_info=True)
            raise MCPError(code=-32603, message=f"Internal ToolForge error: {e}") from e

    async def handle_list_resources(
        self,
        ctx: ServerRequestContext[Any],
        params: t.PaginatedRequestParams | None,
    ) -> t.ListResourcesResult:
        """Map registered ToolForge resources to MCP Resource representations."""
        mcp_resources = []
        if self.resource_registry:
            for tf_resource in self.resource_registry.list():
                mcp_resource = t.Resource(
                    uri=tf_resource.uri,
                    name=tf_resource.name,
                    description=tf_resource.description,
                    mime_type=tf_resource.mime_type,
                )
                mcp_resources.append(mcp_resource)
        return t.ListResourcesResult(resources=mcp_resources)

    async def handle_read_resource(
        self,
        ctx: ServerRequestContext[Any],
        params: t.ReadResourceRequestParams,
    ) -> t.ReadResourceResult:
        """Read the requested resource and return its contents."""
        try:
            if not self.resource_registry:
                raise MCPError(code=-32601, message="Resources are not supported on this server.")

            # 1. Locate the resource
            try:
                tf_resource = self.resource_registry.get(params.uri)
            except ResourceNotFoundError as e:
                raise MCPError(code=-32601, message=str(e)) from e

            # 2. Execute the resource handler
            try:
                import inspect

                if inspect.iscoroutinefunction(tf_resource.fn):
                    raw_result = await tf_resource.fn()
                else:
                    raw_result = tf_resource.fn()
            except Exception as e:
                logger.error(f"Execution failed for resource '{params.uri}': {e}", exc_info=True)
                raise MCPError(code=-32603, message=f"Resource execution failed: {e}") from e

            # 3. Serialize and map the return value to resource contents
            import base64
            import json

            mime_type = tf_resource.mime_type
            if isinstance(raw_result, (dict, list)):
                if mime_type is None:
                    mime_type = "application/json"
                try:
                    serialized_text = json.dumps(raw_result)
                except Exception as json_e:
                    raise MCPError(
                        code=-32603,
                        message=f"Failed to serialize resource content to JSON: {json_e}",
                    ) from json_e

                contents: list[t.TextResourceContents | t.BlobResourceContents] = [
                    t.TextResourceContents(
                        uri=tf_resource.uri,
                        text=serialized_text,
                        mime_type=mime_type,
                    )
                ]
            elif isinstance(raw_result, str):
                contents = [
                    t.TextResourceContents(
                        uri=tf_resource.uri,
                        text=raw_result,
                        mime_type=mime_type,
                    )
                ]
            elif isinstance(raw_result, bytes):
                b64_str = base64.b64encode(raw_result).decode("utf-8")
                contents = [
                    t.BlobResourceContents(
                        uri=tf_resource.uri,
                        blob=b64_str,
                        mime_type=mime_type,
                    )
                ]
            else:
                raise MCPError(
                    code=-32603,
                    message=f"Unsupported resource return type: {type(raw_result).__name__}",
                )

            return t.ReadResourceResult(contents=contents)

        except MCPError:
            raise
        except Exception as e:
            logger.critical(f"Internal ToolForge error in read_resource: {e}", exc_info=True)
            raise MCPError(code=-32603, message=f"Internal ToolForge error: {e}") from e

    async def handle_list_prompts(
        self,
        ctx: ServerRequestContext[Any],
        params: t.PaginatedRequestParams | None,
    ) -> t.ListPromptsResult:
        """Map registered ToolForge prompts to MCP Prompt representations."""
        mcp_prompts = []
        if self.prompt_registry:
            for tf_prompt in self.prompt_registry.list():
                mcp_args = []
                for p_name, p in tf_prompt.parameters.items():
                    mcp_args.append(
                        t.PromptArgument(
                            name=p_name,
                            description=getattr(p, "description", None),
                            required=p.required,
                        )
                    )
                mcp_prompt = t.Prompt(
                    name=tf_prompt.name,
                    description=tf_prompt.description,
                    arguments=mcp_args if mcp_args else None,
                )
                mcp_prompts.append(mcp_prompt)
        return t.ListPromptsResult(prompts=mcp_prompts)

    async def handle_get_prompt(
        self,
        ctx: ServerRequestContext[Any],
        params: t.GetPromptRequestParams,
    ) -> t.GetPromptResult:
        """Get the requested prompt with client arguments."""
        try:
            if not self.prompt_registry:
                raise MCPError(code=-32601, message="Prompts are not supported on this server.")

            # 1. Locate the prompt
            try:
                tf_prompt = self.prompt_registry.get(params.name)
            except ToolNotFoundError as e:
                raise MCPError(code=-32601, message=str(e)) from e

            # 2. Extract and validate/coerce arguments
            raw_args = params.arguments or {}
            from toolforge.validation import validate_prompt_arguments

            try:
                validated_args = validate_prompt_arguments(tf_prompt, raw_args)
            except Exception as val_e:
                raise MCPError(
                    code=-32602, message=f"Prompt argument validation failed: {val_e}"
                ) from val_e

            # 3. Execute prompt template
            try:
                import inspect

                if inspect.iscoroutinefunction(tf_prompt.fn):
                    raw_result = await tf_prompt.fn(**validated_args)
                else:
                    raw_result = tf_prompt.fn(**validated_args)
            except Exception as e:
                logger.error(f"Execution failed for prompt '{params.name}': {e}", exc_info=True)
                raise MCPError(code=-32603, message=f"Prompt execution failed: {e}") from e

            # 4. Map return value to MCP prompt messages format
            messages = []

            def make_text_message(text_val: str, role_val: Any = "user") -> t.PromptMessage:
                return t.PromptMessage(
                    role=role_val,
                    content=t.TextContent(type="text", text=text_val),
                )

            if isinstance(raw_result, str):
                messages.append(make_text_message(raw_result))
            elif isinstance(raw_result, dict):
                role = raw_result.get("role", "user")
                content = raw_result.get("content", "")
                if not isinstance(content, str):
                    tname = type(content).__name__
                    raise MCPError(
                        code=-32603,
                        message=f"Prompt dict content must be a string, received {tname}",
                    )
                messages.append(make_text_message(content, role))
            elif isinstance(raw_result, list):
                for item in raw_result:
                    if isinstance(item, str):
                        messages.append(make_text_message(item))
                    elif isinstance(item, dict):
                        role = item.get("role", "user")
                        content = item.get("content", "")
                        if not isinstance(content, str):
                            tname = type(content).__name__
                            raise MCPError(
                                code=-32603,
                                message=f"Prompt dict content must be a string, received {tname}",
                            )
                        messages.append(make_text_message(content, role))
                    elif isinstance(item, t.PromptMessage):
                        messages.append(item)
                    else:
                        tname = type(item).__name__
                        raise MCPError(
                            code=-32603,
                            message=f"Unsupported item type in prompt result list: {tname}",
                        )
            elif isinstance(raw_result, t.PromptMessage):
                messages.append(raw_result)
            else:
                raise MCPError(
                    code=-32603,
                    message=f"Unsupported prompt return type: {type(raw_result).__name__}",
                )

            return t.GetPromptResult(
                description=tf_prompt.description,
                messages=messages,
            )

        except MCPError:
            raise
        except Exception as e:
            logger.critical(f"Internal ToolForge error in get_prompt: {e}", exc_info=True)
            raise MCPError(code=-32603, message=f"Internal ToolForge error: {e}") from e
