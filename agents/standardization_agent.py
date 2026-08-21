"""
AGENT 2 - Classification & Standardization

Maps raw, inconsistently-named attributes onto a common schema,
normalizes units, and classifies the product into category /
subcategory / family. Uses simple deterministic rules first; falls
back to the LLM only for the semantic classification step.
"""

from __future__ import annotations

from models.product import AttributeStatus, AttributeValue, ExtractionMethod
from models.state import ProductState
from services.llm_service import get_llm_client

# canonical_name: [synonyms...]
ATTRIBUTE_SYNONYMS = {
    "power": ["power rating", "rated power", "motor power", "power"],
    "flow_rate": ["flow rate", "flow", "rated flow"],
    "max_pressure": ["max pressure", "maximum pressure", "pressure rating", "pressure"],
    "material": ["material", "housing material", "construction material"],
}

# (from_unit, to_unit): conversion factor
UNIT_CONVERSIONS = {
    ("w", "kw"): 0.001,
    ("mbar", "bar"): 0.001,
    ("l/min", "m3/h"): 0.06,
    ("gpm", "m3/h"): 0.227,
    ("psi", "bar"): 0.0689476,
    ("hp", "kw"): 0.7457,
}


def _canonical_name(raw_name: str) -> str:
    raw_lower = raw_name.lower().strip()
    for canonical, synonyms in ATTRIBUTE_SYNONYMS.items():
        if raw_lower == canonical or raw_lower in synonyms:
            return canonical
    return raw_name


def _normalize_unit(attr: AttributeValue, canonical_name: str) -> AttributeValue:
    if attr.unit is None or not isinstance(attr.value, (int, float)):
        return attr

    unit_lower = attr.unit.lower()
    target_unit = {"power": "kw", "flow_rate": "m3/h", "max_pressure": "bar"}.get(canonical_name)
    if not target_unit or unit_lower == target_unit:
        return attr

    factor = UNIT_CONVERSIONS.get((unit_lower, target_unit))
    if factor is None:
        return attr  # unsupported/unsafe conversion -- leave as-is rather than guess

    attr.value = round(attr.value * factor, 4)
    attr.unit = target_unit
    attr.method = ExtractionMethod.NORMALIZATION
    attr.status = AttributeStatus.NORMALIZED
    return attr


def _normalize_attributes(state: ProductState) -> None:
    normalized: dict[str, AttributeValue] = {}
    for raw_name, attr in state.attributes.items():
        canonical = _canonical_name(raw_name)
        normalized[canonical] = _normalize_unit(attr, canonical)
    state.attributes = normalized


CLASSIFICATION_SYSTEM_PROMPT = """You are an industrial-product classifier.
Given a short product description, return strict JSON:
{"category": "...", "subcategory": "...", "family": "...", "confidence": 0.0-1.0}
Use standard industrial-equipment taxonomy terms. If uncertain, lower the confidence
and use your best general category rather than leaving fields empty.
"""


def _classify(state: ProductState) -> None:
    client = get_llm_client()
    description = state.product_identity.description
    try:
        result = client.json(CLASSIFICATION_SYSTEM_PROMPT, f"Description: {description}")
    except Exception:
        result = {}

    if result.get("mock"):
        # offline fallback: crude keyword classification so the demo still works
        desc_lower = description.lower()
        if "pump" in desc_lower:
            result = {"category": "Industrial Equipment", "subcategory": "Pumps",
                       "family": "Centrifugal Pumps" if "centrifugal" in desc_lower else "Pumps",
                       "confidence": 0.6}
        elif "motor" in desc_lower:
            result = {"category": "Industrial Equipment", "subcategory": "Motors", "family": "Motors", "confidence": 0.5}
        elif "valve" in desc_lower:
            result = {"category": "Industrial Equipment", "subcategory": "Valves", "family": "Valves", "confidence": 0.5}
        else:
            result = {"category": "Industrial Equipment", "subcategory": "unknown", "family": "unknown", "confidence": 0.3}

    state.classification.category = result.get("category", "unknown")
    state.classification.subcategory = result.get("subcategory", "unknown")
    state.classification.family = result.get("family", "unknown")
    state.classification.confidence = float(result.get("confidence", 0.5))
    state.product_identity.product_name = (
        f"{state.product_identity.part_number} "
        f"{state.classification.family if state.classification.family != 'unknown' else state.product_identity.description}"
    ).strip()


def run(state: ProductState) -> ProductState:
    _normalize_attributes(state)
    _classify(state)
    state.log("standardization_agent", "completed",
               f"category={state.classification.category}, subcategory={state.classification.subcategory}")
    return state
