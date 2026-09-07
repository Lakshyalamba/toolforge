from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from toolforge.intelligence.dataset import MappingDataset, MappingExample
from toolforge.intelligence.metrics import (
    category_match,
    domain_match,
    risk_match,
    semantic_mapping_metric,
)


@dataclass
class EvaluationDetail:
    """Detailed evaluation record for an individual example."""

    tool_name: str
    score: float
    passed: bool
    expected_domain: str = ""
    predicted_domain: str = ""
    expected_category: str = ""
    predicted_category: str = ""
    expected_risk: str = ""
    predicted_risk: str = ""
    improved_description: str = ""


@dataclass
class EvaluationResult:
    """Aggregated results of evaluating a mapper against a dataset."""

    total: int
    passed: int
    mean_score: float
    domain_accuracy: float = 0.0
    category_accuracy: float = 0.0
    risk_accuracy: float = 0.0
    details: list[EvaluationDetail] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Percentage of examples meeting or exceeding the threshold."""
        return (self.passed / self.total * 100.0) if self.total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation result to a serializable dictionary."""
        return {
            "total": self.total,
            "passed": self.passed,
            "pass_rate": round(self.pass_rate, 2),
            "mean_score": round(self.mean_score, 4),
            "domain_accuracy": round(self.domain_accuracy, 4),
            "category_accuracy": round(self.category_accuracy, 4),
            "risk_accuracy": round(self.risk_accuracy, 4),
            "details": [asdict(d) for d in self.details],
        }


class MappingEvaluator:
    """Evaluates semantic tool mapping performance against a benchmark dataset."""

    def __init__(
        self,
        threshold: float = 0.7,
        metric: Callable[..., float] = semantic_mapping_metric,
    ) -> None:
        self.threshold = threshold
        self.metric = metric

    def _get_prediction(self, mapper_or_module: Any, example: MappingExample) -> Any:
        """Obtain a prediction from either a ToolMapper or a raw DSPy Module."""
        from toolforge.intelligence.mapper.base import ToolMapper

        if isinstance(mapper_or_module, ToolMapper):
            # 1. DSPyToolMapper with active enricher module
            enricher = getattr(mapper_or_module, "_enricher", None)
            if enricher is not None and callable(enricher):
                return enricher(
                    tool_name=example.tool_name,
                    docstring=example.description,
                    input_schema=example.input_schema,
                )

            # 2. Any ToolMapper implementation (e.g. StaticToolMapper or fallback)
            from types import SimpleNamespace

            from toolforge.registry import Tool

            temp_tool = Tool(
                fn=lambda: None,
                name=example.tool_name,
                description=example.description,
            )
            res = mapper_or_module.map_tool(temp_tool)
            return SimpleNamespace(
                domain=res.semantics.domain if res.semantics else "general",
                category=res.semantics.category if res.semantics else "utility",
                risk_level=res.semantics.risk_level.value if res.semantics else "unknown",
                improved_description=res.effective_description,
                confidence=res.confidence,
            )

        # 3. Raw callable DSPy Module or function/mock
        if callable(mapper_or_module):
            return mapper_or_module(
                tool_name=example.tool_name,
                docstring=example.description,
                input_schema=example.input_schema,
            )

        raise TypeError(
            f"Unsupported mapper or module type: {type(mapper_or_module).__name__}. "
            "Must be a ToolMapper or callable DSPy module."
        )

    def evaluate(
        self, mapper_or_module: Any, dataset: MappingDataset | list[MappingExample]
    ) -> EvaluationResult:
        """Run evaluation over all examples in the dataset."""
        examples = dataset.examples if isinstance(dataset, MappingDataset) else dataset
        if not examples:
            return EvaluationResult(total=0, passed=0, mean_score=0.0)

        total = len(examples)
        passed = 0
        total_score = 0.0
        details: list[EvaluationDetail] = []

        domain_matches = 0
        domain_total = 0
        category_matches = 0
        category_total = 0
        risk_matches = 0
        risk_total = 0

        for ex in examples:
            pred = self._get_prediction(mapper_or_module, ex)
            score = self.metric(ex, pred)
            total_score += score
            is_passed = score >= self.threshold
            if is_passed:
                passed += 1

            exp_dom = ex.expected_domain or ex.expected_service
            pred_dom = str(getattr(pred, "domain", ""))
            if exp_dom:
                domain_total += 1
                if domain_match(exp_dom, pred_dom) >= 0.8:
                    domain_matches += 1

            exp_cat = ex.expected_category or ex.expected_operation
            pred_cat = str(getattr(pred, "category", ""))
            if exp_cat:
                category_total += 1
                if category_match(exp_cat, pred_cat) >= 0.8:
                    category_matches += 1

            exp_risk = ex.expected_risk_level
            pred_risk = str(getattr(pred, "risk_level", ""))
            if exp_risk:
                risk_total += 1
                if risk_match(exp_risk, pred_risk) >= 0.8:
                    risk_matches += 1

            details.append(
                EvaluationDetail(
                    tool_name=ex.tool_name,
                    score=round(score, 3),
                    passed=is_passed,
                    expected_domain=exp_dom,
                    predicted_domain=pred_dom,
                    expected_category=exp_cat,
                    predicted_category=pred_cat,
                    expected_risk=exp_risk,
                    predicted_risk=pred_risk,
                    improved_description=str(getattr(pred, "improved_description", "")),
                )
            )

        mean_score = total_score / total if total > 0 else 0.0
        domain_acc = (domain_matches / domain_total) if domain_total > 0 else 1.0
        cat_acc = (category_matches / category_total) if category_total > 0 else 1.0
        risk_acc = (risk_matches / risk_total) if risk_total > 0 else 1.0

        return EvaluationResult(
            total=total,
            passed=passed,
            mean_score=mean_score,
            domain_accuracy=domain_acc,
            category_accuracy=cat_acc,
            risk_accuracy=risk_acc,
            details=details,
        )
