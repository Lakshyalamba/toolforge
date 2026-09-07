from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from toolforge.intelligence.errors import DSPyNotInstalledError
from toolforge.intelligence.models import ToolRiskLevel
from toolforge.validation import validate_tool_arguments

if TYPE_CHECKING:
    from toolforge.registry import Tool

try:
    import dspy

    _HAS_DSPY = True
except ImportError:
    dspy = None
    _HAS_DSPY = False


@dataclass
class ToolInvocationRecord:
    """Record of an individual tool call executed by an agent.

    Attributes:
        tool_name: The name of the executed tool.
        arguments: Keyword arguments passed to the tool.
        result: The output returned by the tool, if successful.
        error: The error message if execution or validation failed.
        success: Whether the tool completed without error.
        duration_ms: Execution duration in milliseconds.
        timestamp: Unix timestamp when the call was made.
    """

    tool_name: str
    arguments: dict[str, Any]
    result: Any = None
    error: str | None = None
    success: bool = True
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert record to a dictionary."""
        return asdict(self)


class ToolTrace:
    """Observable trace capturing tool executions for debugging and inspection."""

    def __init__(self) -> None:
        self._records: list[ToolInvocationRecord] = []

    @property
    def records(self) -> list[ToolInvocationRecord]:
        """List of all recorded tool invocations in chronological order."""
        return list(self._records)

    @property
    def last(self) -> ToolInvocationRecord | None:
        """The most recent invocation record, or None if empty."""
        return self._records[-1] if self._records else None

    def record(self, invocation: ToolInvocationRecord) -> None:
        """Append a new invocation record to the trace."""
        self._records.append(invocation)

    def clear(self) -> None:
        """Clear all invocation records."""
        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    def to_dict(self) -> list[dict[str, Any]]:
        """Return all records as a list of dictionaries."""
        return [r.to_dict() for r in self._records]


class DSPyToolAdapter:
    """Adapts a ToolForge Tool for safe, observable execution within DSPy agents."""

    def __init__(
        self,
        tool: Tool,
        trace: ToolTrace | None = None,
        description: str | None = None,
        safety_gate: Callable[[Tool, dict[str, Any]], bool] | None = None,
    ) -> None:
        self.tool = tool
        self.trace = trace if trace is not None else ToolTrace()
        self.name = tool.name
        self.description = (description or tool.description).strip()
        self.safety_gate = safety_gate
        self.args = self._build_clean_args()

    def _build_clean_args(self) -> dict[str, dict[str, Any]]:
        """Extract a clean, minimal parameter schema for the model without internal metadata."""
        schema = self.tool.input_schema
        if not isinstance(schema, dict):
            return {}
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return {}

        clean_args: dict[str, dict[str, Any]] = {}
        for param_name, param_def in properties.items():
            if not isinstance(param_def, dict):
                continue
            param_spec: dict[str, Any] = {}
            if "type" in param_def:
                param_spec["type"] = param_def["type"]
            if param_def.get("description"):
                param_spec["description"] = param_def["description"]
            clean_args[param_name] = param_spec

        return clean_args

    def __call__(self, **kwargs: Any) -> Any:
        """Execute the tool with argument validation, error trapping, and observability."""
        start_time = time.perf_counter()
        timestamp = time.time()

        try:
            validated_args = validate_tool_arguments(self.tool, kwargs)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Tool validation error for '{self.name}': {e}"
            self.trace.record(
                ToolInvocationRecord(
                    tool_name=self.name,
                    arguments=kwargs,
                    error=error_msg,
                    success=False,
                    duration_ms=round(duration_ms, 2),
                    timestamp=timestamp,
                )
            )
            return error_msg

        # Safety gate check before actual execution
        if self.safety_gate is not None:
            try:
                allowed = bool(self.safety_gate(self.tool, validated_args))
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                error_msg = f"Safety gate rejected tool '{self.name}': {e}"
                self.trace.record(
                    ToolInvocationRecord(
                        tool_name=self.name,
                        arguments=validated_args,
                        error=error_msg,
                        success=False,
                        duration_ms=round(duration_ms, 2),
                        timestamp=timestamp,
                    )
                )
                return error_msg

            if not allowed:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                error_msg = f"Safety gate blocked execution of tool '{self.name}'."
                self.trace.record(
                    ToolInvocationRecord(
                        tool_name=self.name,
                        arguments=validated_args,
                        error=error_msg,
                        success=False,
                        duration_ms=round(duration_ms, 2),
                        timestamp=timestamp,
                    )
                )
                return error_msg

        try:
            if inspect.iscoroutinefunction(self.tool.fn):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(asyncio.run, self.tool.fn(**validated_args))
                        result = future.result()
                else:
                    result = asyncio.run(self.tool.fn(**validated_args))
            else:
                result = self.tool.fn(**validated_args)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.trace.record(
                ToolInvocationRecord(
                    tool_name=self.name,
                    arguments=validated_args,
                    result=result,
                    success=True,
                    duration_ms=round(duration_ms, 2),
                    timestamp=timestamp,
                )
            )
            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Tool execution error in '{self.name}': {e}"
            self.trace.record(
                ToolInvocationRecord(
                    tool_name=self.name,
                    arguments=validated_args,
                    error=error_msg,
                    success=False,
                    duration_ms=round(duration_ms, 2),
                    timestamp=timestamp,
                )
            )
            return error_msg


def create_risk_level_safety_gate(
    blocked_risk_levels: set[ToolRiskLevel | str] | None = None,
) -> Callable[[Tool, dict[str, Any]], bool]:
    """Create a safety gate callback that rejects tools matching blocked risk levels.

    Inspects both ``tool.metadata['risk_level']`` and ``tool.tags``.
    Defaults to blocking ``ToolRiskLevel.DESTRUCTIVE`` and ``ToolRiskLevel.FINANCIAL``.

    Args:
        blocked_risk_levels: Set or collection of risk levels to block.

    Returns:
        Safety gate callable accepting ``(tool, args)`` and returning a boolean.
    """
    if blocked_risk_levels is None:
        blocked = {ToolRiskLevel.DESTRUCTIVE.value, ToolRiskLevel.FINANCIAL.value}
    else:
        blocked = {
            r.value if isinstance(r, ToolRiskLevel) else str(r).lower() for r in blocked_risk_levels
        }

    def _gate(tool: Tool, args: dict[str, Any]) -> bool:
        tool_risk = str(tool.metadata.get("risk_level", "")).lower()
        if tool_risk in blocked:
            return False
        return all(tag.lower() not in blocked for tag in getattr(tool, "tags", []))

    return _gate


def to_dspy_tool(
    tool: Tool,
    trace: ToolTrace | None = None,
    description: str | None = None,
    safety_gate: Callable[[Tool, dict[str, Any]], bool] | None = None,
) -> Any:
    """Convert a ToolForge Tool into a DSPy Tool instance.

    Args:
        tool: The ToolForge Tool instance.
        trace: Optional ToolTrace to record invocations.
        description: Optional override description (e.g. from semantic enrichment).
        safety_gate: Optional safety gate callable to validate executions.

    Returns:
        dspy.Tool instance ready for agent use.

    Raises:
        DSPyNotInstalledError: If DSPy is not installed.
    """
    if not _HAS_DSPY or dspy is None:
        raise DSPyNotInstalledError(
            "Converting to a DSPy Tool requires 'dspy'. "
            "Install it via 'pip install \"mcptoolforge[dspy]\"'."
        )

    adapter = DSPyToolAdapter(
        tool,
        trace=trace,
        description=description,
        safety_gate=safety_gate,
    )
    return dspy.Tool(
        func=adapter,
        name=adapter.name,
        desc=adapter.description,
        args=adapter.args,
    )


def to_dspy_tools(
    server_or_tools: Any,
    trace: ToolTrace | None = None,
    safety_gate: Callable[[Tool, dict[str, Any]], bool] | None = None,
) -> list[Any]:
    """Convert multiple ToolForge tools or an MCPServer into a list of DSPy Tool instances.

    Args:
        server_or_tools: MCPServer instance, ToolRegistry, or list of Tool objects.
        trace: Optional shared ToolTrace to record invocations across all tools.
        safety_gate: Optional safety gate callback to protect dangerous tools.

    Returns:
        List of dspy.Tool instances sharing the same trace.
    """
    if hasattr(server_or_tools, "tools"):
        tools = server_or_tools.tools
    elif hasattr(server_or_tools, "list"):
        tools = server_or_tools.list()
    elif isinstance(server_or_tools, (list, tuple)):
        tools = list(server_or_tools)
    else:
        raise TypeError(
            "Expected MCPServer, ToolRegistry, or list of Tool instances, "
            f"got {type(server_or_tools).__name__}"
        )

    shared_trace = trace if trace is not None else ToolTrace()
    return [to_dspy_tool(t, trace=shared_trace, safety_gate=safety_gate) for t in tools]
