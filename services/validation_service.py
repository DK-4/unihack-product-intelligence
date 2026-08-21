"""
Deterministic, rule-based validation used by Agent 4 (Trust/Validation).

Rules are intentionally simple and explainable -- LLM reasoning is
reserved for genuinely semantic judgments elsewhere; here we prefer
plain code wherever code can decide.
"""

from __future__ import annotations

from models.product import AttributeStatus, AttributeValue

REQUIRED_ATTRIBUTES: list[str] = []  # e.g. ["power"] if you want to enforce presence

# attribute_name -> (min, max) sanity bounds; extend as needed per domain
PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "power_kw": (0.01, 5000),
    "max_pressure_bar": (0.1, 1000),
    "flow_rate_m3h": (0.01, 100000),
}

CONFLICT_TOLERANCE_PCT = 0.10  # >10% divergence between sources => conflict


def check_required_fields(attributes: dict[str, AttributeValue]) -> list[str]:
    failures = []
    for req in REQUIRED_ATTRIBUTES:
        if req not in attributes or attributes[req].value in (None, "", "unknown"):
            failures.append(f"Missing required attribute: {req}")
    return failures


def check_types_and_ranges(attributes: dict[str, AttributeValue]) -> list[str]:
    failures = []
    for name, attr in attributes.items():
        if attr.value in (None, "unknown"):
            continue
        range_key = None
        for key in PLAUSIBLE_RANGES:
            if key.split("_")[0] in name.lower():
                range_key = key
                break
        if range_key and isinstance(attr.value, (int, float)):
            low, high = PLAUSIBLE_RANGES[range_key]
            if not (low <= float(attr.value) <= high):
                failures.append(f"Implausible value for '{name}': {attr.value} {attr.unit or ''}".strip())
    return failures


def detect_numeric_conflict(name: str, value_a: float, value_b: float) -> bool:
    if value_a == 0 and value_b == 0:
        return False
    base = max(abs(value_a), abs(value_b), 1e-9)
    return abs(value_a - value_b) / base > CONFLICT_TOLERANCE_PCT


def score_attribute_confidence(attr: AttributeValue) -> float:
    """Nudges confidence based on how well-evidenced the attribute is."""
    score = attr.confidence
    if not attr.evidence:
        score -= 0.1
    if not attr.source:
        score -= 0.1
    if attr.method and str(attr.method) in ("extraction", "pdf_extraction", "direct_input"):
        score += 0.05
    return max(0.0, min(1.0, score))
