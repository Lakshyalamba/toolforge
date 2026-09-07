from __future__ import annotations

import csv
import io
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BenchmarkMetrics:
    """Quantitative evaluation metrics for a tool mapping system.

    Attributes:
        system_name: Name of the evaluated system (e.g. 'Baseline (Static)' or 'DSPy-Enhanced').
        sample_count: Number of benchmark examples evaluated.
        mapping_accuracy: Overall mapping score between 0.0 and 1.0.
        service_id_accuracy: Accuracy of identifying the correct service/domain (0.0 to 1.0).
        operation_id_accuracy: Accuracy of identifying the correct operation/category (0.0 to 1.0).
        invalid_mapping_rate: Percentage of mappings scoring below 0.2 or malformed.
        fallback_rate: Percentage of mappings that used or fell back to static logic.
        avg_latency_ms: Mean wall-clock inference latency per tool in milliseconds.
        total_tokens: Total prompt and completion tokens consumed.
        prompt_tokens: Number of prompt / input tokens.
        completion_tokens: Number of output / completion tokens.
        llm_calls: Number of LLM API requests made.
        failure_rate: Percentage of invocations encountering unhandled exceptions.
    """

    system_name: str
    sample_count: int
    mapping_accuracy: float
    service_id_accuracy: float
    operation_id_accuracy: float
    invalid_mapping_rate: float
    fallback_rate: float
    avg_latency_ms: float
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0
    failure_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to a dictionary."""
        return asdict(self)


@dataclass
class BenchmarkComparison:
    """Comparison of baseline vs DSPy-enhanced systems on an identical benchmark.

    Attributes:
        baseline: Metrics for the baseline (static) mapping system.
        dspy: Metrics for the DSPy-enhanced system.
        timestamp: Unix timestamp when the benchmark was executed.
        metadata: Additional benchmark configuration and environment information.
    """

    baseline: BenchmarkMetrics
    dspy: BenchmarkMetrics
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert comparison to a serializable dictionary."""
        return {
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "baseline": self.baseline.to_dict(),
            "dspy": self.dspy.to_dict(),
            "deltas": {
                "accuracy_delta": round(
                    self.dspy.mapping_accuracy - self.baseline.mapping_accuracy, 4
                ),
                "service_id_delta": round(
                    self.dspy.service_id_accuracy - self.baseline.service_id_accuracy, 4
                ),
                "operation_id_delta": round(
                    self.dspy.operation_id_accuracy - self.baseline.operation_id_accuracy, 4
                ),
                "latency_difference_ms": round(
                    self.dspy.avg_latency_ms - self.baseline.avg_latency_ms, 2
                ),
            },
        }

    def to_json(self, path: str | Path | None = None) -> str:
        """Serialize comparison to JSON, optionally saving to a file."""
        content = json.dumps(self.to_dict(), indent=2) + "\n"
        if path:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content

    def to_csv(self, path: str | Path | None = None) -> str:
        """Serialize comparison metrics to CSV format, optionally saving to a file."""
        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "Metric",
            "Baseline (Static)",
            "DSPy-Enhanced",
            "Delta / Comparison",
        ]
        writer.writerow(headers)

        acc_b = f"{self.baseline.mapping_accuracy * 100:.1f}%"
        acc_d = f"{self.dspy.mapping_accuracy * 100:.1f}%"
        acc_diff = f"{(self.dspy.mapping_accuracy - self.baseline.mapping_accuracy) * 100:+.1f}%"

        srv_b = f"{self.baseline.service_id_accuracy * 100:.1f}%"
        srv_d = f"{self.dspy.service_id_accuracy * 100:.1f}%"
        srv_diff = (
            f"{(self.dspy.service_id_accuracy - self.baseline.service_id_accuracy) * 100:+.1f}%"
        )

        op_b = f"{self.baseline.operation_id_accuracy * 100:.1f}%"
        op_d = f"{self.dspy.operation_id_accuracy * 100:.1f}%"
        op_diff = (
            f"{(self.dspy.operation_id_accuracy - self.baseline.operation_id_accuracy) * 100:+.1f}%"
        )

        inv_b = f"{self.baseline.invalid_mapping_rate * 100:.1f}%"
        inv_d = f"{self.dspy.invalid_mapping_rate * 100:.1f}%"
        inv_diff = (
            f"{(self.dspy.invalid_mapping_rate - self.baseline.invalid_mapping_rate) * 100:+.1f}%"
        )

        fb_b = f"{self.baseline.fallback_rate * 100:.1f}%"
        fb_d = f"{self.dspy.fallback_rate * 100:.1f}%"
        fb_diff = f"{(self.dspy.fallback_rate - self.baseline.fallback_rate) * 100:+.1f}%"

        lat_b = f"{self.baseline.avg_latency_ms:.2f} ms"
        lat_d = f"{self.dspy.avg_latency_ms:.2f} ms"
        lat_diff = f"{self.dspy.avg_latency_ms - self.baseline.avg_latency_ms:+.2f} ms"

        tok_diff = f"{self.dspy.total_tokens - self.baseline.total_tokens:+d}"
        calls_diff = f"{self.dspy.llm_calls - self.baseline.llm_calls:+d}"

        fail_b = f"{self.baseline.failure_rate * 100:.1f}%"
        fail_d = f"{self.dspy.failure_rate * 100:.1f}%"
        fail_diff = f"{(self.dspy.failure_rate - self.baseline.failure_rate) * 100:+.1f}%"

        rows: list[list[Any]] = [
            ["Sample Count", self.baseline.sample_count, self.dspy.sample_count, "Identical"],
            ["Mapping Accuracy", acc_b, acc_d, acc_diff],
            ["Correct Service ID", srv_b, srv_d, srv_diff],
            ["Correct Operation ID", op_b, op_d, op_diff],
            ["Invalid Mapping Rate", inv_b, inv_d, inv_diff],
            ["Fallback Rate", fb_b, fb_d, fb_diff],
            ["Avg Latency (ms)", lat_b, lat_d, lat_diff],
            ["Total Tokens", self.baseline.total_tokens, self.dspy.total_tokens, tok_diff],
            ["LLM API Calls", self.baseline.llm_calls, self.dspy.llm_calls, calls_diff],
            ["Failure Rate", fail_b, fail_d, fail_diff],
        ]

        for row in rows:
            writer.writerow(row)

        csv_content = output.getvalue()
        if path:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(csv_content, encoding="utf-8")
        return csv_content

    def to_markdown_table(self) -> str:
        """Render human-readable Markdown comparison table."""
        acc_b = f"{self.baseline.mapping_accuracy * 100:.1f}%"
        acc_d = f"{self.dspy.mapping_accuracy * 100:.1f}%"
        acc_diff = f"{(self.dspy.mapping_accuracy - self.baseline.mapping_accuracy) * 100:+.1f}%"

        srv_b = f"{self.baseline.service_id_accuracy * 100:.1f}%"
        srv_d = f"{self.dspy.service_id_accuracy * 100:.1f}%"
        srv_diff = (
            f"{(self.dspy.service_id_accuracy - self.baseline.service_id_accuracy) * 100:+.1f}%"
        )

        op_b = f"{self.baseline.operation_id_accuracy * 100:.1f}%"
        op_d = f"{self.dspy.operation_id_accuracy * 100:.1f}%"
        op_diff = (
            f"{(self.dspy.operation_id_accuracy - self.baseline.operation_id_accuracy) * 100:+.1f}%"
        )

        inv_b = f"{self.baseline.invalid_mapping_rate * 100:.1f}%"
        inv_d = f"{self.dspy.invalid_mapping_rate * 100:.1f}%"
        inv_diff = (
            f"{(self.dspy.invalid_mapping_rate - self.baseline.invalid_mapping_rate) * 100:+.1f}%"
        )

        fb_b = f"{self.baseline.fallback_rate * 100:.1f}%"
        fb_d = f"{self.dspy.fallback_rate * 100:.1f}%"
        fb_diff = f"{(self.dspy.fallback_rate - self.baseline.fallback_rate) * 100:+.1f}%"

        lat_b = f"{self.baseline.avg_latency_ms:.2f} ms"
        lat_d = f"{self.dspy.avg_latency_ms:.2f} ms"
        lat_diff = f"{self.dspy.avg_latency_ms - self.baseline.avg_latency_ms:+.2f} ms"

        fail_b = f"{self.baseline.failure_rate * 100:.1f}%"
        fail_d = f"{self.dspy.failure_rate * 100:.1f}%"
        fail_diff = f"{(self.dspy.failure_rate - self.baseline.failure_rate) * 100:+.1f}%"

        tok_b = self.baseline.total_tokens
        tok_d = self.dspy.total_tokens
        calls_b = self.baseline.llm_calls
        calls_d = self.dspy.llm_calls

        lines = [
            "| Metric | Baseline (Static) | DSPy-Enhanced | Delta / Comparison |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Tool Mapping Accuracy** | {acc_b} | {acc_d} | {acc_diff} |",
            f"| **Correct Service ID** | {srv_b} | {srv_d} | {srv_diff} |",
            f"| **Correct Operation ID** | {op_b} | {op_d} | {op_diff} |",
            f"| **Invalid Mapping Rate** | {inv_b} | {inv_d} | {inv_diff} |",
            f"| **Fallback Rate** | {fb_b} | {fb_d} | {fb_diff} |",
            f"| **Avg Inference Latency** | {lat_b} | {lat_d} | {lat_diff} |",
            f"| **Total Tokens** | {tok_b} | {tok_d} | +{tok_d} |",
            f"| **LLM Calls** | {calls_b} | {calls_d} | +{calls_d} |",
            f"| **Failure Rate** | {fail_b} | {fail_d} | {fail_diff} |",
        ]
        return "\n".join(lines)
