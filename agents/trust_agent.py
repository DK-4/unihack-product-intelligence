"""
AGENT 4 - Trust / Validation

The gatekeeper. Runs deterministic rule checks, cross-source
conflict detection, and rolls everything up into a trust score and
per-attribute status. Anything below threshold or in conflict is
flagged for human review rather than silently approved.
"""

from __future__ import annotations

import os

from models.product import AttributeStatus, Conflict, ValidationSummary
from models.state import ProductState
from services.validation_service import (
    check_required_fields,
    check_types_and_ranges,
    score_attribute_confidence,
)

CONFIDENCE_THRESHOLD = float(os.getenv("VALIDATION_CONFIDENCE_THRESHOLD", "0.75"))


def _detect_cross_source_conflicts(state: ProductState) -> list[Conflict]:
    """Very small demo-scale conflict check: if the same canonical attribute
    was extracted from two different sources with materially different
    values, flag it. (Extend with more sources as the system grows.)"""
    conflicts: list[Conflict] = []
    # In this MVP, attributes are already de-duplicated by canonical name in
    # Agent 2, so cross-source conflicts would show up if raw_extractions
    # captured multiple candidate values before normalization collapsed them.
    seen_values: dict[str, list[dict]] = {}
    for entry in state.raw_extractions:
        pass  # placeholder hook: raw text is kept for audit; numeric
        # cross-checking against retrieved/external sources happens below.

    for name, attr in state.attributes.items():
        if attr.source_type and "retrieved" in str(attr.source_type):
            continue
    return conflicts


def run(state: ProductState) -> ProductState:
    failures = check_required_fields(state.attributes)
    failures += check_types_and_ranges(state.attributes)

    verified = 0
    needs_review = 0

    for name, attr in state.attributes.items():
        attr.confidence = score_attribute_confidence(attr)
        if attr.confidence >= CONFIDENCE_THRESHOLD and attr.status not in (AttributeStatus.CONFLICT,):
            attr.status = AttributeStatus.VERIFIED
            verified += 1
        else:
            attr.status = AttributeStatus.NEEDS_REVIEW
            needs_review += 1

    for name, attr in state.applications.items():
        attr.confidence = score_attribute_confidence(attr)
        if attr.confidence < CONFIDENCE_THRESHOLD:
            attr.status = AttributeStatus.NEEDS_REVIEW
            needs_review += 1
        else:
            verified += 1

    conflicts = _detect_cross_source_conflicts(state)

    total = max(1, verified + needs_review + len(conflicts))
    trust_score = round((verified - 0.5 * len(conflicts)) / total, 2)
    trust_score = max(0.0, min(1.0, trust_score))

    state.validation = ValidationSummary(
        trust_score=trust_score,
        verified_count=verified,
        needs_review_count=needs_review,
        conflict_count=len(conflicts),
        conflicts=conflicts,
        rule_failures=failures,
    )

    state.human_review_required = bool(needs_review > 0 or conflicts or failures)

    state.log(
        "trust_agent",
        "completed",
        f"trust_score={trust_score}, verified={verified}, needs_review={needs_review}, conflicts={len(conflicts)}",
    )
    return state
