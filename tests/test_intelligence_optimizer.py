import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from toolforge.config import DSPyConfig, DSPyOptimizationConfig
from toolforge.intelligence.dataset import MappingDataset, MappingExample
from toolforge.intelligence.errors import OptimizationError
from toolforge.intelligence.evaluator import EvaluationResult, MappingEvaluator
from toolforge.intelligence.mapper.dspy_mapper import DSPyToolMapper
from toolforge.intelligence.optimizer import (
    MapperOptimizer,
    load_optimized_program,
    save_optimized_program,
)
from toolforge.registry import Tool


def test_evaluation_result_properties() -> None:
    res = EvaluationResult(
        total=4,
        passed=3,
        mean_score=0.85,
        domain_accuracy=1.0,
        category_accuracy=0.75,
        risk_accuracy=1.0,
    )
    assert res.pass_rate == 75.0
    data = res.to_dict()
    assert data["total"] == 4
    assert data["passed"] == 3
    assert data["pass_rate"] == 75.0
    assert data["mean_score"] == 0.85


def test_mapping_evaluator_with_mock_enricher() -> None:
    dataset = MappingDataset.from_list(
        [
            {
                "tool_name": "t1",
                "expected_domain": "database",
                "expected_category": "mutation",
                "expected_risk_level": "destructive",
            },
            {
                "tool_name": "t2",
                "expected_domain": "filesystem",
                "expected_category": "query",
                "expected_risk_level": "safe",
            },
        ]
    )

    mock_enricher = MagicMock()
    # First example matches perfectly, second mismatches on domain
    mock_enricher.side_effect = [
        SimpleNamespace(
            domain="database",
            category="mutation",
            risk_level="destructive",
            improved_description="Deletes records cleanly.",
        ),
        SimpleNamespace(
            domain="network",  # mismatch
            category="query",
            risk_level="safe",
            improved_description="Queries file data.",
        ),
    ]

    evaluator = MappingEvaluator(threshold=0.8)
    res = evaluator.evaluate(mock_enricher, dataset)

    assert res.total == 2
    assert res.passed == 1
    assert res.domain_accuracy == 0.5
    assert res.category_accuracy == 1.0
    assert res.risk_accuracy == 1.0
    assert len(res.details) == 2
    assert res.details[0].passed is True
    assert res.details[1].passed is False


def test_mapping_evaluator_empty_dataset() -> None:
    evaluator = MappingEvaluator()
    res = evaluator.evaluate(MagicMock(), MappingDataset([]))
    assert res.total == 0
    assert res.passed == 0
    assert res.mean_score == 0.0


def test_save_and_load_optimized_program(tmp_path: Path) -> None:
    from toolforge.intelligence.modules import ToolEnricherModule

    original_enricher = ToolEnricherModule()
    program_path = tmp_path / "compiled_enricher.json"

    save_optimized_program(
        original_enricher,
        program_path,
        metadata={"metric_score": 0.95, "model": "test-model"},
    )

    assert program_path.exists()
    meta_path = program_path.with_suffix(".meta.json")
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["metric_score"] == 0.95

    loaded_enricher = load_optimized_program(program_path)
    assert isinstance(loaded_enricher, ToolEnricherModule)


def test_save_program_invalid_module() -> None:
    with pytest.raises(OptimizationError, match="does not have a 'save' method"):
        save_optimized_program("not_a_module", "path.json")


def test_load_program_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_optimized_program("/non/existent/path/prog.json")


def test_dspy_tool_mapper_from_compiled(tmp_path: Path) -> None:
    from toolforge.intelligence.modules import ToolEnricherModule

    program_path = tmp_path / "prog.json"
    module = ToolEnricherModule()
    save_optimized_program(module, program_path)

    mapper = DSPyToolMapper.from_compiled(str(program_path))
    assert mapper.compiled is True

    # Test mapping produces mapping_source = 'dspy_compiled'
    mock_prediction = SimpleNamespace(
        domain="testing",
        category="utility",
        risk_level="safe",
        improved_description="Improved doc",
        negative_examples=[],
        confidence=0.9,
    )
    mapper._enricher = MagicMock(return_value=mock_prediction)

    tool = Tool(
        fn=lambda: True,
        name="test_tool",
        description="Original doc",
    )
    res = mapper.map_tool(tool)
    assert res.mapping_source == "dspy_compiled"
    assert res.confidence == 0.9
    assert res.effective_description == "Improved doc"


def test_dspy_tool_mapper_from_config(tmp_path: Path) -> None:
    from toolforge.intelligence.modules import ToolEnricherModule

    program_path = tmp_path / "saved_prog.json"
    save_optimized_program(ToolEnricherModule(), program_path)

    # Valid path in config
    cfg = DSPyConfig(
        enabled=True,
        confidence_threshold=0.8,
        compiled_program_path=str(program_path),
    )
    mapper = DSPyToolMapper.from_config(cfg)
    assert mapper.compiled is True
    assert mapper.confidence_threshold == 0.8

    # Non-existent path in config falls back gracefully when strict=False
    bad_cfg = DSPyConfig(
        enabled=True,
        compiled_program_path="/non/existent/prog.json",
    )
    fallback_mapper = DSPyToolMapper.from_config(bad_cfg, strict=False)
    assert fallback_mapper.compiled is False

    # Strict raises
    with pytest.raises(FileNotFoundError):
        DSPyToolMapper.from_config(bad_cfg, strict=True)


def test_mapper_optimizer_empty_trainset() -> None:
    optimizer = MapperOptimizer()
    mapper = DSPyToolMapper()
    with pytest.raises(OptimizationError, match="trainset cannot be empty"):
        optimizer.compile(mapper, trainset=[])


def test_mapper_optimizer_invalid_student() -> None:
    optimizer = MapperOptimizer()
    with pytest.raises(OptimizationError, match="not a valid DSPy module"):
        optimizer.compile(
            "not_a_module",
            trainset=[MappingExample(tool_name="t", expected_domain="d")],
        )


def test_optimization_config_validations() -> None:
    opt = DSPyOptimizationConfig(
        enabled=True,
        max_bootstrapped_demos=4,
        max_labeled_demos=3,
        metric_threshold=0.85,
    )
    assert opt.max_bootstrapped_demos == 4
    assert opt.max_labeled_demos == 3
    assert opt.metric_threshold == 0.85
