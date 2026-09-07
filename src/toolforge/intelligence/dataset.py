import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from toolforge.intelligence.errors import DatasetValidationError, DSPyNotInstalledError

try:
    import dspy

    _HAS_DSPY = True
except ImportError:
    dspy = None
    _HAS_DSPY = False


@dataclass
class MappingExample:
    """A known-correct example of semantic tool mapping or intent routing.

    Attributes:
        tool_name: The identifier of the tool.
        description: The docstring or human-readable description of the tool.
        input_schema: JSON Schema dictionary describing tool parameters.
        expected_service: Expected service / API group identifier.
        expected_operation: Expected operation / endpoint / category identifier.
        expected_domain: Expected functional domain (e.g. 'database', 'web', 'filesystem').
        expected_category: Expected operational category (e.g. 'mutation', 'query').
        expected_risk_level: Expected risk assessment ('safe', 'idempotent', 'destructive').
        intent: Optional natural language query or intent for disambiguation testing.
        expected_tool: Optional target tool name to select for the intent.
        expected_arguments: Optional extracted argument values.
        metadata: Optional arbitrary extra metadata for evaluation tracking.
    """

    tool_name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    expected_service: str = ""
    expected_operation: str = ""
    expected_domain: str = ""
    expected_category: str = ""
    expected_risk_level: str = ""
    intent: str = ""
    expected_tool: str = ""
    expected_arguments: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.tool_name, str) or not self.tool_name.strip():
            raise DatasetValidationError("MappingExample 'tool_name' must be a non-empty string.")
        self.tool_name = self.tool_name.strip()

        if not isinstance(self.description, str):
            raise DatasetValidationError(
                f"MappingExample for tool '{self.tool_name}': 'description' must be a string."
            )

        if not isinstance(self.input_schema, dict):
            raise DatasetValidationError(
                f"MappingExample for tool '{self.tool_name}': 'input_schema' must be a dictionary."
            )

        # Validate that at least one expectation is defined
        has_enrichment_expectation = any(
            bool(val and isinstance(val, str) and val.strip())
            for val in (
                self.expected_service,
                self.expected_operation,
                self.expected_domain,
                self.expected_category,
                self.expected_risk_level,
            )
        )
        has_intent_expectation = bool(self.intent and (self.expected_tool or self.tool_name))

        if not (has_enrichment_expectation or has_intent_expectation):
            raise DatasetValidationError(
                f"MappingExample for tool '{self.tool_name}' must specify at least one expected "
                f"target (e.g., 'expected_service', 'expected_operation', 'expected_domain', "
                f"'expected_category', 'expected_risk_level', or 'expected_tool')."
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert this example to a clean dictionary."""
        return asdict(self)

    def to_dspy_example(self) -> Any:
        """Convert this example to a DSPy Example instance configured with inputs."""
        if not _HAS_DSPY or dspy is None:
            raise DSPyNotInstalledError(
                "Cannot convert to dspy.Example because 'dspy' is not installed."
            )

        schema_str = json.dumps(self.input_schema)

        # Build output fields for enrichment / classification
        resolved_domain = self.expected_domain or self.expected_service
        resolved_category = self.expected_category or self.expected_operation

        example_kwargs: dict[str, Any] = {
            "tool_name": self.tool_name,
            "docstring": self.description,
            "input_schema": schema_str,
            "domain": resolved_domain,
            "category": resolved_category,
            "risk_level": self.expected_risk_level,
            "expected_service": self.expected_service,
            "expected_operation": self.expected_operation,
        }

        if self.intent:
            example_kwargs["intent"] = self.intent
            example_kwargs["selected_tool"] = self.expected_tool or self.tool_name

        ex = dspy.Example(**example_kwargs)
        if self.intent:
            return ex.with_inputs("intent", "candidate_tools")
        return ex.with_inputs("tool_name", "docstring", "input_schema")


class MappingDataset:
    """Dataset container holding known-correct tool mapping examples.

    Supports loading and saving from JSON and JSONL formats.
    """

    def __init__(self, examples: list[MappingExample] | None = None) -> None:
        self.examples: list[MappingExample] = examples or []

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> MappingExample:
        return self.examples[index]

    def __iter__(self):
        return iter(self.examples)

    def add(self, example: MappingExample) -> None:
        """Append an example to the dataset."""
        if not isinstance(example, MappingExample):
            raise TypeError(f"Expected MappingExample, got {type(example).__name__}")
        self.examples.append(example)

    @classmethod
    def from_list(cls, items: Sequence[dict[str, Any] | MappingExample]) -> "MappingDataset":
        """Construct a dataset from a list of dictionaries or MappingExample objects."""
        examples: list[MappingExample] = []
        for i, item in enumerate(items):
            if isinstance(item, MappingExample):
                examples.append(item)
            elif isinstance(item, dict):
                try:
                    examples.append(MappingExample(**item))
                except TypeError as e:
                    raise DatasetValidationError(
                        f"Invalid field in example at index {i}: {e}"
                    ) from e
            else:
                raise DatasetValidationError(
                    f"Item at index {i} must be a dict or MappingExample, "
                    f"got {type(item).__name__}."
                )
        return cls(examples)

    @classmethod
    def from_file(cls, path: str | Path) -> "MappingDataset":
        """Load and parse dataset from a JSON or JSONL file.

        Args:
            path: Filesystem path to the dataset file.

        Raises:
            FileNotFoundError: If the file does not exist.
            DatasetValidationError: If parsing or validating fails.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: '{file_path}'")

        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            return cls([])

        is_jsonl = file_path.suffix.lower() == ".jsonl"

        if is_jsonl:
            items: list[dict[str, Any]] = []
            for line_no, line in enumerate(content.splitlines(), start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                except json.JSONDecodeError as e:
                    raise DatasetValidationError(
                        f"Failed to parse JSONL line {line_no} in '{file_path}': {e}"
                    ) from e
                if not isinstance(data, dict):
                    raise DatasetValidationError(
                        f"Expected JSON object on line {line_no} in '{file_path}', "
                        f"got {type(data).__name__}"
                    )
                items.append(data)
            return cls.from_list(items)

        # Standard JSON parsing
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise DatasetValidationError(f"Failed to parse JSON from '{file_path}': {e}") from e

        if isinstance(parsed, list):
            return cls.from_list(parsed)
        elif isinstance(parsed, dict) and "examples" in parsed:
            examples_list = parsed["examples"]
            if not isinstance(examples_list, list):
                raise DatasetValidationError(f"Field 'examples' in '{file_path}' must be a list.")
            return cls.from_list(examples_list)
        else:
            raise DatasetValidationError(
                f"Root of dataset file '{file_path}' must be a JSON array "
                "or an object with an 'examples' array."
            )

    def save(self, path: str | Path, format: str = "json") -> None:
        """Save dataset to a file in json or jsonl format."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "jsonl" or file_path.suffix.lower() == ".jsonl":
            lines = [json.dumps(ex.to_dict()) for ex in self.examples]
            file_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        else:
            data = [ex.to_dict() for ex in self.examples]
            file_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def to_dspy_examples(self) -> list[Any]:
        """Convert all examples to dspy.Example objects."""
        return [ex.to_dspy_example() for ex in self.examples]
