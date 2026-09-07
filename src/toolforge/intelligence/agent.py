from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from toolforge.intelligence.errors import DSPyNotInstalledError
from toolforge.intelligence.tools import ToolInvocationRecord, ToolTrace, to_dspy_tools

if TYPE_CHECKING:
    from toolforge.registry import Tool

try:
    import dspy

    _HAS_DSPY = True
except ImportError:
    dspy = None
    _HAS_DSPY = False


if _HAS_DSPY:

    class ToolForgeAgentSignature(dspy.Signature):
        """Answer the user request by selecting and executing appropriate tools."""

        question: str = dspy.InputField(desc="The user query or task instruction")
        answer: str = dspy.OutputField(desc="Final answer or response addressing the user request")

else:
    ToolForgeAgentSignature = None  # type: ignore[assignment, misc]


@dataclass
class AgentResult:
    """The result returned by a ToolForgeAgent run.

    Attributes:
        response: The final synthesized answer or output.
        tool_calls: Chronological list of tool invocations executed during the run.
        success: Whether the agent run completed successfully.
        raw_prediction: Raw DSPy prediction object, if available.
    """

    response: str
    tool_calls: list[ToolInvocationRecord] = field(default_factory=list)
    success: bool = True
    raw_prediction: Any = None

    @property
    def tools_used(self) -> list[str]:
        """List of unique tool names called during this run."""
        seen: set[str] = set()
        res: list[str] = []
        for call in self.tool_calls:
            if call.tool_name not in seen:
                seen.add(call.tool_name)
                res.append(call.tool_name)
        return res

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a dictionary."""
        return {
            "response": self.response,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "tools_used": self.tools_used,
            "success": self.success,
        }


class ToolForgeAgent:
    """Agent that reasons over user requests, selects ToolForge tools, and executes them."""

    def __init__(
        self,
        server_or_tools: Any,
        lm: Any = None,
        max_iters: int = 5,
        trace: ToolTrace | None = None,
        safety_gate: Callable[[Tool, dict[str, Any]], bool] | None = None,
    ) -> None:
        if not _HAS_DSPY or dspy is None:
            raise DSPyNotInstalledError(
                "ToolForgeAgent requires 'dspy'. "
                "Install it via 'pip install \"mcptoolforge[dspy]\"'."
            )

        self.trace = trace if trace is not None else ToolTrace()
        self.safety_gate = safety_gate
        self.dspy_tools = to_dspy_tools(
            server_or_tools,
            trace=self.trace,
            safety_gate=self.safety_gate,
        )
        self.lm = lm
        self.max_iters = max_iters

        self.react = dspy.ReAct(
            signature=ToolForgeAgentSignature,
            tools=self.dspy_tools,
            max_iters=self.max_iters,
        )

    def run(self, query: str, **kwargs: Any) -> AgentResult:
        """Run the agent on a user query, selecting and executing tools as needed.

        Args:
            query: The user query or task.
            **kwargs: Extra arguments passed to the underlying DSPy program.

        Returns:
            AgentResult containing the final response and tool invocation trace.
        """
        start_index = len(self.trace)

        try:
            if self.lm is not None:
                with dspy.context(lm=self.lm):
                    pred = self.react(question=query, **kwargs)
            else:
                pred = self.react(question=query, **kwargs)

            new_calls = self.trace.records[start_index:]
            raw_answer = getattr(pred, "answer", "") or str(pred)

            return AgentResult(
                response=raw_answer.strip(),
                tool_calls=new_calls,
                success=True,
                raw_prediction=pred,
            )

        except Exception as e:
            new_calls = self.trace.records[start_index:]
            return AgentResult(
                response=f"Agent failed to execute: {e}",
                tool_calls=new_calls,
                success=False,
                raw_prediction=None,
            )
