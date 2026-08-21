from agents.standardization_agent import _canonical_name, _normalize_unit
from models.product import AttributeValue
from services.validation_service import check_types_and_ranges, score_attribute_confidence


def test_canonical_name_mapping():
    assert _canonical_name("Rated Power") == "power"
    assert _canonical_name("Motor Power") == "power"
    assert _canonical_name("power") == "power"


def test_unit_normalization_w_to_kw():
    attr = AttributeValue(value=5500, unit="w")
    normalized = _normalize_unit(attr, "power")
    assert normalized.value == 5.5
    assert normalized.unit == "kw"


def test_unit_normalization_mbar_to_bar():
    attr = AttributeValue(value=10000, unit="mbar")
    normalized = _normalize_unit(attr, "max_pressure")
    assert normalized.value == 10.0
    assert normalized.unit == "bar"


def test_implausible_value_flagged():
    attrs = {"power_kw": AttributeValue(value=999999, unit="kw")}
    failures = check_types_and_ranges(attrs)
    assert any("Implausible" in f for f in failures)


def test_confidence_scoring_penalizes_missing_evidence():
    attr = AttributeValue(value=5.5, unit="kW", confidence=0.9, source=None, evidence=None)
    score = score_attribute_confidence(attr)
    assert score < 0.9
