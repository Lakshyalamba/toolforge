import json
from pathlib import Path
from types import SimpleNamespace

from toolforge.intelligence.benchmark import (
    BENCHMARK_EXAMPLES,
    BenchmarkComparison,
    BenchmarkMetrics,
    BenchmarkRunner,
    get_default_benchmark_dataset,
)
from toolforge.intelligence.dataset import MappingDataset, MappingExample
from toolforge.intelligence.mapper.dspy_mapper import DSPyToolMapper
from toolforge.intelligence.mapper.static import StaticToolMapper


def test_default_benchmark_dataset():
    """Verify built-in benchmark dataset structure and contents."""
    dataset = get_default_benchmark_dataset()
    assert len(dataset) == 10
    assert len(BENCHMARK_EXAMPLES) == 10

    for ex in dataset:
        assert isinstance(ex, MappingExample)
        assert ex.tool_name
        assert ex.description
        assert isinstance(ex.input_schema, dict)
        assert ex.expected_service
        assert ex.expected_risk_level in [
            "safe",
            "idempotent",
            "destructive",
            "financial",
            "unknown",
        ]


def test_benchmark_metrics_serialization():
    """Verify BenchmarkMetrics serialization to dict."""
    metrics = BenchmarkMetrics(
        system_name="TestSystem",
        sample_count=5,
        mapping_accuracy=0.85,
        service_id_accuracy=0.9,
        operation_id_accuracy=0.8,
        invalid_mapping_rate=0.1,
        fallback_rate=0.2,
        avg_latency_ms=12.5,
        total_tokens=150,
        prompt_tokens=100,
        completion_tokens=50,
        llm_calls=3,
        failure_rate=0.0,
    )
    d = metrics.to_dict()
    assert d["system_name"] == "TestSystem"
    assert d["sample_count"] == 5
    assert d["mapping_accuracy"] == 0.85
    assert d["avg_latency_ms"] == 12.5
    assert d["total_tokens"] == 150


def test_benchmark_comparison_serialization(tmp_path: Path):
    """Verify BenchmarkComparison exports to JSON, CSV, and Markdown."""
    baseline = BenchmarkMetrics(
        system_name="Baseline (Static)",
        sample_count=10,
        mapping_accuracy=0.0,
        service_id_accuracy=0.0,
        operation_id_accuracy=0.0,
        invalid_mapping_rate=1.0,
        fallback_rate=1.0,
        avg_latency_ms=0.05,
        total_tokens=0,
        prompt_tokens=0,
        completion_tokens=0,
        llm_calls=0,
    )
    dspy_m = BenchmarkMetrics(
        system_name="DSPy-Enhanced",
        sample_count=10,
        mapping_accuracy=0.92,
        service_id_accuracy=0.90,
        operation_id_accuracy=0.90,
        invalid_mapping_rate=0.0,
        fallback_rate=0.0,
        avg_latency_ms=150.0,
        total_tokens=1200,
        prompt_tokens=900,
        completion_tokens=300,
        llm_calls=10,
    )
    comp = BenchmarkComparison(baseline=baseline, dspy=dspy_m)

    # 1. JSON
    json_path = tmp_path / "results.json"
    json_str = comp.to_json(json_path)
    assert json_path.exists()
    parsed = json.loads(json_str)
    assert parsed["deltas"]["accuracy_delta"] == 0.92
    assert parsed["deltas"]["latency_difference_ms"] == 149.95

    # 2. CSV
    csv_path = tmp_path / "results.csv"
    csv_str = comp.to_csv(csv_path)
    assert csv_path.exists()
    assert "Tool Mapping Accuracy" in csv_str or "Mapping Accuracy" in csv_str
    assert "92.0%" in csv_str

    # 3. Markdown
    md_str = comp.to_markdown_table()
    assert "| Metric | Baseline (Static) | DSPy-Enhanced | Delta / Comparison |" in md_str
    assert "**Tool Mapping Accuracy**" in md_str
    assert "92.0%" in md_str


def test_benchmark_runner_empty_dataset():
    """Verify runner behavior with an empty dataset."""
    runner = BenchmarkRunner()
    metrics = runner.evaluate_system("Test", StaticToolMapper(), MappingDataset([]))
    assert metrics.sample_count == 0
    assert metrics.mapping_accuracy == 0.0


def test_benchmark_runner_baseline():
    """Verify baseline evaluation produces expected zero-token static results."""
    dataset = get_default_benchmark_dataset()
    runner = BenchmarkRunner()

    metrics = runner.evaluate_system(
        "Baseline (Static)",
        StaticToolMapper(),
        dataset,
        track_lm=False,
    )

    assert metrics.sample_count == 10
    assert metrics.mapping_accuracy == 0.0  # Static mapper does not perform semantic classification
    assert metrics.service_id_accuracy == 0.0
    assert metrics.operation_id_accuracy == 0.0
    assert metrics.fallback_rate == 1.0  # All tools mapped statically
    assert metrics.invalid_mapping_rate == 1.0
    assert metrics.avg_latency_ms >= 0.0
    assert metrics.total_tokens == 0
    assert metrics.llm_calls == 0
    assert metrics.failure_rate == 0.0


def test_benchmark_runner_dspy_with_mock():
    """Verify DSPy evaluation against a mock enricher achieving high accuracy."""
    dataset = get_default_benchmark_dataset()

    def mock_enricher(tool_name: str, docstring: str, input_schema: dict):
        # Look up corresponding example
        for ex in BENCHMARK_EXAMPLES:
            if ex["tool_name"] == tool_name:
                return SimpleNamespace(
                    domain=ex["expected_service"],
                    category=ex["expected_category"],
                    primary_intent=ex["description"],
                    risk_level=ex["expected_risk_level"],
                    improved_description="Optimized clear docstring for LLM agent selection.",
                    negative_examples=[],
                    confidence=0.95,
                )
        return SimpleNamespace(
            domain="general",
            category="utility",
            primary_intent="",
            risk_level="safe",
            improved_description="Generic tool description.",
            negative_examples=[],
            confidence=0.5,
        )

    mock_dspy_mapper = DSPyToolMapper(enricher_module=mock_enricher)
    runner = BenchmarkRunner(dspy_mapper=mock_dspy_mapper)

    comparison = runner.run(dataset=dataset)

    # Baseline
    assert comparison.baseline.mapping_accuracy == 0.0
    assert comparison.baseline.fallback_rate == 1.0

    # DSPy
    assert comparison.dspy.mapping_accuracy > 0.90
    assert comparison.dspy.service_id_accuracy == 1.0
    assert comparison.dspy.operation_id_accuracy == 1.0
    assert comparison.dspy.invalid_mapping_rate == 0.0
    assert comparison.dspy.fallback_rate == 0.0
    assert comparison.dspy.failure_rate == 0.0


def test_benchmark_cli_command(tmp_path: Path, capsys):
    """Verify CLI benchmark command execution and file export."""
    from toolforge.cli.commands import benchmark_command

    out_json = str(tmp_path / "cli_bench.json")
    out_csv = str(tmp_path / "cli_bench.csv")

    benchmark_command(output_json=out_json, output_csv=out_csv)

    captured = capsys.readouterr()
    assert "ToolForge Quantitative Benchmark" in captured.out
    assert "Results Summary:" in captured.out
    assert "Saved machine-readable JSON results to:" in captured.out
    assert "Saved machine-readable CSV results to:" in captured.out

    assert Path(out_json).exists()
    assert Path(out_csv).exists()

    with open(out_json, encoding="utf-8") as f:
        data = json.load(f)
    assert "baseline" in data
    assert "dspy" in data
    assert "deltas" in data
