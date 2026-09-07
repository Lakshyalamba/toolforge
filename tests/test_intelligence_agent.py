import asyncio
from unittest.mock import MagicMock

import pytest

from toolforge import MCPServer
from toolforge.intelligence.agent import AgentResult, ToolForgeAgent
from toolforge.intelligence.tools import (
    DSPyToolAdapter,
    ToolInvocationRecord,
    ToolTrace,
)
from toolforge.registry import Tool


def test_tool_invocation_record() -> None:
    rec = ToolInvocationRecord(
        tool_name="add",
        arguments={"a": 2, "b": 3},
        result=5,
        duration_ms=1.25,
    )
    assert rec.tool_name == "add"
    assert rec.arguments == {"a": 2, "b": 3}
    assert rec.result == 5
    assert rec.success is True
    assert rec.duration_ms == 1.25

    data = rec.to_dict()
    assert data["tool_name"] == "add"
    assert data["success"] is True


def test_tool_trace() -> None:
    trace = ToolTrace()
    assert len(trace) == 0
    assert trace.last is None

    rec1 = ToolInvocationRecord(tool_name="t1", arguments={})
    rec2 = ToolInvocationRecord(tool_name="t2", arguments={})
    trace.record(rec1)
    trace.record(rec2)

    assert len(trace) == 2
    assert trace.last == rec2
    assert [r.tool_name for r in trace] == ["t1", "t2"]
    assert len(trace.to_dict()) == 2

    trace.clear()
    assert len(trace) == 0


def test_dspy_tool_adapter_sync_execution() -> None:
    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""
        return a * b

    tool = Tool(fn=multiply, name="multiply", description="Multiply two numbers.")
    trace = ToolTrace()
    adapter = DSPyToolAdapter(tool, trace=trace)

    assert adapter.name == "multiply"
    assert adapter.description == "Multiply two numbers."
    assert "a" in adapter.args
    assert adapter.args["a"]["type"] == "integer"

    # Execute successfully
    res = adapter(a=6, b=7)
    assert res == 42
    assert len(trace) == 1
    assert trace.last.tool_name == "multiply"
    assert trace.last.success is True
    assert trace.last.result == 42
    assert trace.last.duration_ms >= 0.0


def test_dspy_tool_adapter_async_execution() -> None:
    async def async_fetch(url: str) -> str:
        """Fetch content asynchronously."""
        await asyncio.sleep(0.01)
        return f"Content from {url}"

    tool = Tool(fn=async_fetch, name="fetch")
    trace = ToolTrace()
    adapter = DSPyToolAdapter(tool, trace=trace)

    res = adapter(url="https://example.com")
    assert res == "Content from https://example.com"
    assert len(trace) == 1
    assert trace.last.success is True
    assert trace.last.result == "Content from https://example.com"


def test_dspy_tool_adapter_validation_error() -> None:
    def add(a: int, b: int) -> int:
        """Add integers."""
        return a + b

    tool = Tool(fn=add, name="add")
    trace = ToolTrace()
    adapter = DSPyToolAdapter(tool, trace=trace)

    # Pass invalid type (string instead of integer)
    res = adapter(a="not_an_int", b=5)
    assert "Tool validation error for 'add'" in res
    assert len(trace) == 1
    assert trace.last.success is False
    assert "Tool validation error" in trace.last.error


def test_dspy_tool_adapter_runtime_exception() -> None:
    def divide(a: int, b: int) -> float:
        """Divide numbers."""
        return a / b

    tool = Tool(fn=divide, name="divide")
    trace = ToolTrace()
    adapter = DSPyToolAdapter(tool, trace=trace)

    # Division by zero
    res = adapter(a=10, b=0)
    assert "Tool execution error in 'divide'" in res
    assert len(trace) == 1
    assert trace.last.success is False
    assert "division by zero" in trace.last.error


def test_to_dspy_tool_and_convenience_methods() -> None:
    dspy = pytest.importorskip("dspy")

    def echo(msg: str) -> str:
        """Echo a message."""
        return msg

    tool = Tool(fn=echo, name="echo")
    dspy_tool = tool.as_dspy_tool()

    assert isinstance(dspy_tool, dspy.Tool)
    assert dspy_tool.name == "echo"
    assert dspy_tool(msg="hello") == "hello"


def test_to_dspy_tools_from_server() -> None:
    dspy = pytest.importorskip("dspy")

    server = MCPServer("agent_test_server")

    @server.tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @server.tool
    def subtract(a: int, b: int) -> int:
        """Subtract b from a."""
        return a - b

    trace = ToolTrace()
    dspy_tools = server.as_dspy_tools(trace=trace)

    assert len(dspy_tools) == 2
    assert all(isinstance(t, dspy.Tool) for t in dspy_tools)

    # Execute tools and check shared trace
    res1 = dspy_tools[0](a=10, b=5)
    res2 = dspy_tools[1](a=10, b=3)

    assert res1 == 15
    assert res2 == 7
    assert len(trace) == 2
    assert trace.records[0].tool_name == "add"
    assert trace.records[1].tool_name == "subtract"


def test_agent_result_properties() -> None:
    rec1 = ToolInvocationRecord(tool_name="tool_a", arguments={"x": 1})
    rec2 = ToolInvocationRecord(tool_name="tool_b", arguments={"y": 2})
    rec3 = ToolInvocationRecord(tool_name="tool_a", arguments={"x": 3})

    res = AgentResult(
        response="All calculations complete.",
        tool_calls=[rec1, rec2, rec3],
        success=True,
    )
    assert res.response == "All calculations complete."
    assert res.tools_used == ["tool_a", "tool_b"]
    data = res.to_dict()
    assert data["response"] == "All calculations complete."
    assert len(data["tool_calls"]) == 3
    assert data["tools_used"] == ["tool_a", "tool_b"]
    assert data["success"] is True


def test_toolforge_agent_initialization_and_run() -> None:
    server = MCPServer("calc_server")

    @server.tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    agent = ToolForgeAgent(server, max_iters=3)
    assert len(agent.dspy_tools) == 1
    assert agent.dspy_tools[0].name == "add"

    # Mock ReAct forward execution that calls tool
    mock_prediction = MagicMock()
    mock_prediction.answer = "The sum is 15."

    def mock_react_call(*args, **kwargs):
        agent.dspy_tools[0](a=10, b=5)
        return mock_prediction

    agent.react = MagicMock(side_effect=mock_react_call)

    result = agent.run("What is 10 + 5?")
    assert result.success is True
    assert result.response == "The sum is 15."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "add"
    assert result.tool_calls[0].result == 15


def test_toolforge_agent_error_handling() -> None:
    server = MCPServer("fail_server")

    @server.tool
    def ping() -> str:
        return "pong"

    agent = ToolForgeAgent(server)
    agent.react = MagicMock(side_effect=RuntimeError("Model connection failed"))

    result = agent.run("ping")
    assert result.success is False
    assert "Agent failed to execute" in result.response
    assert "Model connection failed" in result.response


def test_dspy_tool_adapter_safety_gate_blocked() -> None:
    executed = False

    def delete_records(table: str) -> str:
        nonlocal executed
        executed = True
        return f"Deleted {table}"

    tool = Tool(
        fn=delete_records,
        name="delete_records",
        metadata={"risk_level": "destructive"},
    )
    trace = ToolTrace()

    # Safety gate returns False to deny execution
    def reject_all(t, args):
        return False

    adapter = DSPyToolAdapter(tool, trace=trace, safety_gate=reject_all)
    res = adapter(table="users")

    assert executed is False
    assert "Safety gate blocked execution of tool 'delete_records'" in res
    assert len(trace) == 1
    assert trace.last.success is False
    assert "Safety gate blocked execution" in trace.last.error


def test_dspy_tool_adapter_safety_gate_allowed() -> None:
    executed = False

    def safe_query(table: str) -> str:
        nonlocal executed
        executed = True
        return f"Results from {table}"

    tool = Tool(fn=safe_query, name="safe_query")
    trace = ToolTrace()

    def allow_all(t, args):
        return True

    adapter = DSPyToolAdapter(tool, trace=trace, safety_gate=allow_all)
    res = adapter(table="users")

    assert executed is True
    assert res == "Results from users"
    assert len(trace) == 1
    assert trace.last.success is True


def test_dspy_tool_adapter_safety_gate_exception() -> None:
    def dangerous_op() -> str:
        return "done"

    tool = Tool(fn=dangerous_op, name="dangerous_op")
    trace = ToolTrace()

    def buggy_gate(t, args):
        raise PermissionError("Access denied by security policy")

    adapter = DSPyToolAdapter(tool, trace=trace, safety_gate=buggy_gate)
    res = adapter()

    assert "Safety gate rejected tool 'dangerous_op'" in res
    assert "Access denied by security policy" in res
    assert len(trace) == 1
    assert trace.last.success is False


def test_create_risk_level_safety_gate() -> None:
    from toolforge.intelligence.models import ToolRiskLevel
    from toolforge.intelligence.tools import create_risk_level_safety_gate

    gate = create_risk_level_safety_gate()

    # Destructive tool blocked by metadata
    t_destructive = Tool(
        fn=lambda: None,
        name="drop_db",
        metadata={"risk_level": "destructive"},
    )
    assert gate(t_destructive, {}) is False

    # Financial tool blocked by metadata
    t_financial = Tool(
        fn=lambda: None,
        name="charge_card",
        metadata={"risk_level": "financial"},
    )
    assert gate(t_financial, {}) is False

    # Blocked by tag
    t_tagged = Tool(
        fn=lambda: None,
        name="wipe_disk",
        tags=["destructive"],
    )
    assert gate(t_tagged, {}) is False

    # Safe tool allowed
    t_safe = Tool(
        fn=lambda: None,
        name="get_weather",
        metadata={"risk_level": "safe"},
    )
    assert gate(t_safe, {}) is True

    # Custom blocked set
    custom_gate = create_risk_level_safety_gate(blocked_risk_levels={ToolRiskLevel.SAFE})
    assert custom_gate(t_safe, {}) is False
    assert custom_gate(t_destructive, {}) is True


def test_toolforge_agent_with_safety_gate() -> None:
    server = MCPServer("safe_agent_server")

    executed = False

    @server.tool(metadata={"risk_level": "destructive"})
    def wipe_database() -> str:
        nonlocal executed
        executed = True
        return "Database wiped"

    from toolforge.intelligence.tools import create_risk_level_safety_gate

    gate = create_risk_level_safety_gate()
    agent = ToolForgeAgent(server, safety_gate=gate)

    # Mock ReAct calling the tool
    mock_prediction = MagicMock()
    mock_prediction.answer = "Tool execution completed."

    def mock_react_call(*args, **kwargs):
        # Attempt to call the blocked tool
        _ = agent.dspy_tools[0]()
        return mock_prediction

    agent.react = MagicMock(side_effect=mock_react_call)

    result = agent.run("Wipe the database now.")
    assert executed is False
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].success is False
    assert "Safety gate blocked execution" in result.tool_calls[0].error
