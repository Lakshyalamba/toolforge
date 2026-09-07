from types import SimpleNamespace

from toolforge.intelligence.dataset import MappingExample
from toolforge.intelligence.metrics import (
    category_match,
    domain_match,
    risk_match,
    semantic_mapping_metric,
    tool_selection_match,
)


def test_domain_match_exact_and_variations() -> None:
    assert domain_match("database", "database") == 1.0
    assert domain_match("database_service", "database") == 1.0
    assert domain_match("database", "database-api") == 1.0
    assert domain_match("db", "database") == 1.0  # alias
    assert domain_match("data", "database") == 0.8  # substring
    assert domain_match("database", "filesystem") == 0.0
    assert domain_match("", "database") == 0.0


def test_category_match() -> None:
    assert category_match("mutation", "mutation") == 1.0
    assert category_match("query", "query") == 1.0
    assert category_match("mut", "mutation") == 0.8
    assert category_match("query", "mutation") == 0.0
    assert category_match("analytics", "") == 0.0


def test_risk_match() -> None:
    assert risk_match("destructive", "destructive") == 1.0
    assert risk_match("safe", "safe") == 1.0
    assert risk_match("safe", "destructive") == 0.0
    assert risk_match("", "safe") == 0.0


def test_tool_selection_match() -> None:
    assert tool_selection_match("delete_partition", "delete_partition") == 1.0
    assert tool_selection_match("delete_partition", "DELETE_PARTITION") == 1.0
    assert tool_selection_match("delete_partition", "get_user") == 0.0
    assert tool_selection_match("", "delete_partition") == 0.0


def test_semantic_mapping_metric_perfect_score() -> None:
    ex = MappingExample(
        tool_name="delete_user",
        expected_domain="identity",
        expected_category="mutation",
        expected_risk_level="destructive",
    )
    pred = SimpleNamespace(
        domain="identity",
        category="mutation",
        risk_level="destructive",
        improved_description="Permanently deletes a user account and associated credentials.",
    )
    score = semantic_mapping_metric(ex, pred)
    assert score == 1.0


def test_semantic_mapping_metric_service_operation_naming() -> None:
    ex = MappingExample(
        tool_name="query_logs",
        expected_service="logging_service",
        expected_operation="read_operation",
        expected_risk_level="safe",
    )
    pred = SimpleNamespace(
        domain="logging",
        category="read",
        risk_level="safe",
        improved_description="Retrieves structured log entries matching the filter criteria.",
    )
    score = semantic_mapping_metric(ex, pred)
    assert score >= 0.95


def test_semantic_mapping_metric_partial_score() -> None:
    ex = MappingExample(
        tool_name="update_config",
        expected_domain="system",
        expected_category="configuration",
        expected_risk_level="idempotent",
    )
    # Domain matches, category mismatches, risk matches
    pred = SimpleNamespace(
        domain="system",
        category="unknown",
        risk_level="idempotent",
        improved_description="Updates runtime settings.",
    )
    score = semantic_mapping_metric(ex, pred)
    assert 0.5 < score < 1.0


def test_semantic_mapping_metric_complete_mismatch() -> None:
    ex = MappingExample(
        tool_name="reboot_node",
        expected_domain="infrastructure",
        expected_category="lifecycle",
        expected_risk_level="destructive",
    )
    pred = SimpleNamespace(
        domain="accounting",
        category="reporting",
        risk_level="safe",
        improved_description="",
    )
    score = semantic_mapping_metric(ex, pred)
    assert score == 0.0


def test_semantic_mapping_metric_intent_selection() -> None:
    ex = MappingExample(
        tool_name="delete_account",
        intent="Wipe user credentials",
        expected_tool="delete_account",
    )
    pred_correct = SimpleNamespace(selected_tool="delete_account")
    assert semantic_mapping_metric(ex, pred_correct) == 1.0

    pred_wrong = SimpleNamespace(selected_tool="view_account")
    assert semantic_mapping_metric(ex, pred_wrong) == 0.0
