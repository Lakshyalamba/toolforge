from __future__ import annotations

import logging
import time
from types import SimpleNamespace
from typing import Any

from toolforge.intelligence.benchmark.dataset import get_default_benchmark_dataset
from toolforge.intelligence.benchmark.models import (
    BenchmarkComparison,
    BenchmarkMetrics,
)
from toolforge.intelligence.dataset import MappingDataset
from toolforge.intelligence.mapper.base import ToolMapper
from toolforge.intelligence.mapper.dspy_mapper import DSPyToolMapper
from toolforge.intelligence.mapper.static import StaticToolMapper
from toolforge.intelligence.metrics import (
    category_match,
    domain_match,
    semantic_mapping_metric,
)
from toolforge.intelligence.models import ToolMappingResult
from toolforge.registry import Tool

logger = logging.getLogger("toolforge.intelligence.benchmark")


class BenchmarkTool(Tool):
    """Synthetic Tool wrapper allowing custom input schemas for benchmarking."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(fn=lambda: None, name=name, description=description)
        self._custom_input_schema = input_schema or {"type": "object", "properties": {}}

    @property
    def input_schema(self) -> dict[str, Any]:
        return self._custom_input_schema


class BenchmarkRunner:
    """Orchestrates side-by-side quantitative benchmarking between Baseline and DSPy mappers."""

    def __init__(
        self,
        static_mapper: ToolMapper | None = None,
        dspy_mapper: ToolMapper | None = None,
    ) -> None:
        self.static_mapper = static_mapper or StaticToolMapper()
        self.dspy_mapper = dspy_mapper or DSPyToolMapper()

    def evaluate_system(
        self,
        system_name: str,
        mapper: ToolMapper,
        dataset: MappingDataset,
        track_lm: bool = False,
    ) -> BenchmarkMetrics:
        """Run benchmark on a single mapper against the provided dataset."""
        if len(dataset) == 0:
            return BenchmarkMetrics(
                system_name=system_name,
                sample_count=0,
                mapping_accuracy=0.0,
                service_id_accuracy=0.0,
                operation_id_accuracy=0.0,
                invalid_mapping_rate=0.0,
                fallback_rate=0.0,
                avg_latency_ms=0.0,
            )

        lm = None
        start_hist_len = 0
        if track_lm:
            try:
                import dspy

                lm = getattr(dspy.settings, "lm", None)
                if lm is not None and hasattr(lm, "history"):
                    start_hist_len = len(lm.history)
            except ImportError:
                pass

        latencies_ms: list[float] = []
        scores: list[float] = []
        correct_services = 0
        correct_operations = 0
        fallback_count = 0
        invalid_count = 0
        failure_count = 0

        for example in dataset:
            tool = BenchmarkTool(
                name=example.tool_name,
                description=example.description,
                input_schema=example.input_schema,
            )

            start_t = time.perf_counter()
            mapping_res: ToolMappingResult | None = None
            try:
                mapping_res = mapper.map_tool(tool)
            except Exception as exc:
                logger.warning(f"Error mapping tool '{example.tool_name}' in {system_name}: {exc}")
                failure_count += 1
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            latencies_ms.append(elapsed_ms)

            if mapping_res is None:
                scores.append(0.0)
                invalid_count += 1
                fallback_count += 1
                continue

            # Check fallback
            if mapping_res.mapping_source == "static" or not mapping_res.is_enriched:
                fallback_count += 1

            # Extract semantics
            domain = mapping_res.semantics.domain if mapping_res.semantics else ""
            category = mapping_res.semantics.category if mapping_res.semantics else ""
            risk = (
                mapping_res.semantics.risk_level.value
                if (mapping_res.semantics and mapping_res.semantics.risk_level)
                else ""
            )
            improved_desc = (
                mapping_res.semantics.improved_description if mapping_res.semantics else ""
            )

            prediction = SimpleNamespace(
                domain=domain,
                category=category,
                risk_level=risk,
                improved_description=improved_desc,
            )

            # Evaluate score
            score = semantic_mapping_metric(example, prediction)
            scores.append(score)
            if score < 0.20:
                invalid_count += 1

            # Service accuracy
            exp_service = getattr(example, "expected_service", "")
            exp_domain = getattr(example, "expected_domain", "")
            if (exp_service and domain_match(exp_service, domain) >= 0.8) or (
                exp_domain and domain_match(exp_domain, domain) >= 0.8
            ):
                correct_services += 1

            # Operation accuracy
            exp_op = getattr(example, "expected_operation", "")
            exp_cat = getattr(example, "expected_category", "")
            if (exp_op and category_match(exp_op, category) >= 0.8) or (
                exp_cat and category_match(exp_cat, category) >= 0.8
            ):
                correct_operations += 1

        # Token and LLM tracking
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        llm_calls = 0

        if lm is not None and hasattr(lm, "history"):
            end_hist_len = len(lm.history)
            entries = lm.history[start_hist_len:end_hist_len]
            llm_calls = len(entries)
            for entry in entries:
                usage = entry.get("usage", {}) or {}
                p_tok = usage.get("prompt_tokens", 0) or 0
                c_tok = usage.get("completion_tokens", 0) or 0
                t_tok = usage.get("total_tokens", p_tok + c_tok) or 0
                prompt_tokens += p_tok
                completion_tokens += c_tok
                total_tokens += t_tok

        n = len(dataset)
        return BenchmarkMetrics(
            system_name=system_name,
            sample_count=n,
            mapping_accuracy=round(sum(scores) / n, 4),
            service_id_accuracy=round(correct_services / n, 4),
            operation_id_accuracy=round(correct_operations / n, 4),
            invalid_mapping_rate=round(invalid_count / n, 4),
            fallback_rate=round(fallback_count / n, 4),
            avg_latency_ms=round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else 0.0,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            llm_calls=llm_calls,
            failure_rate=round(failure_count / n, 4),
        )

    def run(
        self,
        dataset: MappingDataset | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BenchmarkComparison:
        """Execute baseline and DSPy evaluations on the same benchmark dataset."""
        ds = dataset if dataset is not None else get_default_benchmark_dataset()

        baseline_metrics = self.evaluate_system(
            system_name="Baseline (Static)",
            mapper=self.static_mapper,
            dataset=ds,
            track_lm=False,
        )

        dspy_metrics = self.evaluate_system(
            system_name="DSPy-Enhanced",
            mapper=self.dspy_mapper,
            dataset=ds,
            track_lm=True,
        )

        run_metadata = {
            "dataset_size": len(ds),
            "dspy_ready": getattr(self.dspy_mapper, "is_dspy_ready", False),
        }
        if metadata:
            run_metadata.update(metadata)

        return BenchmarkComparison(
            baseline=baseline_metrics,
            dspy=dspy_metrics,
            metadata=run_metadata,
        )
