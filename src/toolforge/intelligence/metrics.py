from typing import Any


def _normalize_token(val: Any) -> str:
    """Helper to cleanly normalize semantic category/domain strings."""
    if not val:
        return ""
    token = str(val).strip().lower()
    # Normalize common suffix variations
    for suffix in (
        "_service",
        "-service",
        "_api",
        "-api",
        "_operation",
        "-operation",
        "_method",
        "-method",
    ):
        if token.endswith(suffix):
            token = token[: -len(suffix)]
            break

    # Normalize common aliases
    aliases = {
        "db": "database",
        "fs": "filesystem",
        "net": "network",
        "auth": "authentication",
        "cfg": "configuration",
    }
    return aliases.get(token.strip(), token.strip())


def domain_match(expected: str, predicted: str) -> float:
    """Evaluate whether the predicted domain matches the expected service/domain."""
    exp = _normalize_token(expected)
    pred = _normalize_token(predicted)
    if not exp or not pred:
        return 0.0
    if exp == pred:
        return 1.0
    if exp in pred or pred in exp:
        return 0.8
    return 0.0


def category_match(expected: str, predicted: str) -> float:
    """Evaluate whether the predicted category matches the expected operation/category."""
    exp = _normalize_token(expected)
    pred = _normalize_token(predicted)
    if not exp or not pred:
        return 0.0
    if exp == pred:
        return 1.0
    if exp in pred or pred in exp:
        return 0.8
    return 0.0


def risk_match(expected: str, predicted: str) -> float:
    """Evaluate whether the predicted risk level matches the expected risk level."""
    exp = _normalize_token(expected)
    pred = _normalize_token(predicted)
    if not exp or not pred:
        return 0.0
    if exp == pred:
        return 1.0
    return 0.0


def tool_selection_match(expected_tool: str, predicted_tool: str) -> float:
    """Evaluate whether the predicted tool selection matches the expected tool."""
    exp = str(expected_tool).strip().lower()
    pred = str(predicted_tool).strip().lower()
    if not exp or not pred:
        return 0.0
    return 1.0 if exp == pred else 0.0


def semantic_mapping_metric(example: Any, prediction: Any, trace: Any = None) -> float:
    """DSPy-compatible metric evaluating predicted mapping against expected mapping.

    Signature: (example, prediction, trace=None) -> float in [0.0, 1.0].
    Dynamically weights evaluated fields depending on which expected fields are specified.
    """
    scores: list[float] = []
    weights: list[float] = []

    # 1. Intent-based Tool Disambiguation (if present)
    expected_tool = getattr(example, "expected_tool", "") or getattr(example, "tool_name", "")
    predicted_tool = getattr(prediction, "selected_tool", "")
    if getattr(example, "intent", "") and predicted_tool:
        score = tool_selection_match(expected_tool, predicted_tool)
        scores.append(score)
        weights.append(1.0)
        # Disambiguation task is evaluated purely on tool selection accuracy
        return sum(s * w for s, w in zip(scores, weights, strict=True)) / sum(weights)

    # 2. Domain / Service matching
    expected_domain = getattr(example, "expected_domain", "") or getattr(
        example, "expected_service", ""
    )
    if expected_domain:
        pred_domain = getattr(prediction, "domain", "")
        scores.append(domain_match(expected_domain, pred_domain))
        weights.append(0.35)

    # 3. Category / Operation matching
    expected_category = getattr(example, "expected_category", "") or getattr(
        example, "expected_operation", ""
    )
    if expected_category:
        pred_cat = getattr(prediction, "category", "")
        scores.append(category_match(expected_category, pred_cat))
        weights.append(0.35)

    # 4. Risk Level matching
    expected_risk = getattr(example, "expected_risk_level", "")
    if expected_risk:
        pred_risk = getattr(prediction, "risk_level", "")
        scores.append(risk_match(expected_risk, pred_risk))
        weights.append(0.20)

    # 5. Enrichment description quality bonus
    improved_desc = getattr(prediction, "improved_description", "")
    if improved_desc and len(improved_desc.strip()) > 10:
        scores.append(1.0)
        weights.append(0.10)
    elif scores:
        # If expected fields exist but improved description was empty, slight penalty
        scores.append(0.0)
        weights.append(0.10)

    if not weights:
        # Fallback if example had no recognized fields
        return 1.0 if getattr(prediction, "improved_description", "") else 0.5

    return sum(s * w for s, w in zip(scores, weights, strict=True)) / sum(weights)
