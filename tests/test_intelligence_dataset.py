import json

import pytest

from toolforge.intelligence.dataset import MappingDataset, MappingExample
from toolforge.intelligence.errors import DatasetValidationError


def test_mapping_example_valid() -> None:
    ex = MappingExample(
        tool_name="delete_user",
        description="Delete a user account by ID.",
        input_schema={"type": "object", "properties": {"user_id": {"type": "integer"}}},
        expected_domain="user_management",
        expected_category="mutation",
        expected_risk_level="destructive",
    )
    assert ex.tool_name == "delete_user"
    assert ex.expected_domain == "user_management"
    data = ex.to_dict()
    assert data["tool_name"] == "delete_user"
    assert data["expected_risk_level"] == "destructive"


def test_mapping_example_validation_failures() -> None:
    # Empty tool name
    with pytest.raises(DatasetValidationError, match="non-empty string"):
        MappingExample(tool_name="")

    # Non-string description
    with pytest.raises(DatasetValidationError, match="'description' must be a string"):
        MappingExample(tool_name="tool", description=123)  # type: ignore[arg-type]

    # Non-dict input schema
    with pytest.raises(DatasetValidationError, match="'input_schema' must be a dictionary"):
        MappingExample(tool_name="tool", input_schema="not_a_dict")  # type: ignore[arg-type]

    # No expected fields defined
    with pytest.raises(DatasetValidationError, match="must specify at least one expected target"):
        MappingExample(tool_name="tool")


def test_mapping_example_intent_expectation() -> None:
    ex = MappingExample(
        tool_name="wipe_db",
        intent="Delete all database partitions",
        expected_tool="wipe_db",
    )
    assert ex.intent == "Delete all database partitions"
    assert ex.expected_tool == "wipe_db"


def test_mapping_example_to_dspy_example() -> None:
    ex = MappingExample(
        tool_name="read_file",
        description="Read file content.",
        input_schema={"type": "object"},
        expected_domain="filesystem",
        expected_category="query",
        expected_risk_level="safe",
    )
    dspy_ex = ex.to_dspy_example()
    assert dspy_ex.tool_name == "read_file"
    assert dspy_ex.docstring == "Read file content."
    assert dspy_ex.domain == "filesystem"
    assert dspy_ex.category == "query"
    assert dspy_ex.risk_level == "safe"
    assert "tool_name" in dspy_ex._input_keys


def test_mapping_dataset_from_list() -> None:
    items = [
        {
            "tool_name": "backup_db",
            "description": "Backup DB",
            "expected_service": "database",
            "expected_operation": "backup",
            "expected_risk_level": "safe",
        },
        MappingExample(
            tool_name="restore_db",
            description="Restore DB",
            expected_service="database",
            expected_operation="restore",
            expected_risk_level="destructive",
        ),
    ]
    dataset = MappingDataset.from_list(items)
    assert len(dataset) == 2
    assert dataset[0].tool_name == "backup_db"
    assert dataset[1].tool_name == "restore_db"


def test_mapping_dataset_from_list_invalid() -> None:
    with pytest.raises(DatasetValidationError, match="Invalid field in example"):
        MappingDataset.from_list([{"tool_name": "t1", "unsupported_field": 123}])

    with pytest.raises(DatasetValidationError, match="must be a dict or MappingExample"):
        MappingDataset.from_list(["not_a_dict"])  # type: ignore[list-item]


def test_mapping_dataset_from_json_file(tmp_path) -> None:
    data = [
        {
            "tool_name": "fetch_user",
            "description": "Fetch user by ID",
            "expected_domain": "identity",
            "expected_category": "query",
            "expected_risk_level": "safe",
        }
    ]
    file_path = tmp_path / "dataset.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    dataset = MappingDataset.from_file(file_path)
    assert len(dataset) == 1
    assert dataset[0].tool_name == "fetch_user"


def test_mapping_dataset_from_json_envelope(tmp_path) -> None:
    data = {
        "examples": [
            {
                "tool_name": "query_logs",
                "description": "Query audit logs",
                "expected_domain": "logging",
                "expected_category": "query",
                "expected_risk_level": "safe",
            }
        ]
    }
    file_path = tmp_path / "dataset_envelope.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    dataset = MappingDataset.from_file(file_path)
    assert len(dataset) == 1
    assert dataset[0].tool_name == "query_logs"


def test_mapping_dataset_from_jsonl_file(tmp_path) -> None:
    lines = [
        json.dumps(
            {
                "tool_name": "ping",
                "description": "Health check",
                "expected_service": "system",
                "expected_operation": "status",
                "expected_risk_level": "safe",
            }
        ),
        json.dumps(
            {
                "tool_name": "restart",
                "description": "Restart service",
                "expected_service": "system",
                "expected_operation": "lifecycle",
                "expected_risk_level": "destructive",
            }
        ),
    ]
    file_path = tmp_path / "dataset.jsonl"
    file_path.write_text("\n".join(lines), encoding="utf-8")

    dataset = MappingDataset.from_file(file_path)
    assert len(dataset) == 2
    assert dataset[0].tool_name == "ping"
    assert dataset[1].tool_name == "restart"


def test_mapping_dataset_empty_file(tmp_path) -> None:
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    dataset = MappingDataset.from_file(empty_file)
    assert len(dataset) == 0


def test_mapping_dataset_save_and_roundtrip(tmp_path) -> None:
    original = MappingDataset.from_list(
        [
            {
                "tool_name": "create_item",
                "description": "Create an item",
                "expected_domain": "inventory",
                "expected_category": "mutation",
                "expected_risk_level": "idempotent",
            }
        ]
    )
    # Save as JSON
    json_path = tmp_path / "out.json"
    original.save(json_path, format="json")
    loaded_json = MappingDataset.from_file(json_path)
    assert len(loaded_json) == 1
    assert loaded_json[0].tool_name == "create_item"

    # Save as JSONL
    jsonl_path = tmp_path / "out.jsonl"
    original.save(jsonl_path, format="jsonl")
    loaded_jsonl = MappingDataset.from_file(jsonl_path)
    assert len(loaded_jsonl) == 1
    assert loaded_jsonl[0].tool_name == "create_item"


def test_mapping_dataset_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        MappingDataset.from_file("/non/existent/path/dataset.json")


def test_mapping_dataset_malformed_json(tmp_path) -> None:
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{this is not json", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="Failed to parse JSON"):
        MappingDataset.from_file(bad_json)


def test_mapping_dataset_malformed_jsonl(tmp_path) -> None:
    bad_jsonl = tmp_path / "bad.jsonl"
    bad_jsonl.write_text(
        '{"tool_name": "ok", "expected_domain": "a"}\n{bad json line',
        encoding="utf-8",
    )
    with pytest.raises(DatasetValidationError, match="Failed to parse JSONL line 2"):
        MappingDataset.from_file(bad_jsonl)
