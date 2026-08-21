"""
AGENT 1 - Discovery / Extraction

Pulls as much reliable information as possible out of the raw inputs
(user-typed fields, PDF datasheet, product image) and writes it into
ProductState as evidence-backed AttributeValues. Nothing here is
invented -- every value written here traces back to a concrete source.
"""

from __future__ import annotations

import re

from models.product import AttributeStatus, AttributeValue, ExtractionMethod, SourceType
from models.state import ProductState
from services.pdf_service import extract_pdf, find_snippet_page
from services.vision_service import analyze_image

# very small starter set of spec patterns; extend as needed
SPEC_PATTERNS = {
    "power": re.compile(r"(?:power|motor power|rated power)\s*[:\-]?\s*([\d.,]+)\s*(kw|w|hp)", re.I),
    "flow_rate": re.compile(r"(?:flow rate|flow)\s*[:\-]?\s*([\d.,]+)\s*(m3/h|m³/h|l/min|gpm)", re.I),
    "max_pressure": re.compile(r"(?:max(?:imum)? pressure|pressure)\s*[:\-]?\s*([\d.,]+)\s*(bar|mbar|psi)", re.I),
    "material": re.compile(r"(?:material|housing|construction)\s*[:\-]?\s*(stainless steel|cast iron|carbon steel|aluminum|bronze|plastic|pvc)", re.I),
}


def _from_user_input(state: ProductState) -> None:
    ident = state.product_identity
    state.attributes["part_number"] = AttributeValue(
        value=ident.part_number,
        confidence=1.0,
        source="user_input",
        source_type=SourceType.USER_INPUT,
        method=ExtractionMethod.DIRECT_INPUT,
        status=AttributeStatus.VERIFIED,
        evidence=ident.part_number,
    )
    state.attributes["brand"] = AttributeValue(
        value=ident.brand,
        confidence=1.0,
        source="user_input",
        source_type=SourceType.USER_INPUT,
        method=ExtractionMethod.DIRECT_INPUT,
        status=AttributeStatus.VERIFIED,
        evidence=ident.brand,
    )
    state.raw_extractions.append({"source": "user_input", "field": "description", "text": ident.description})


def _from_pdf(state: ProductState) -> None:
    if not state.pdf_path:
        return
    result = extract_pdf(state.pdf_path)
    if not result.success:
        state.log("discovery_agent", "pdf_extraction_failed", result.error)
        return

    state.raw_extractions.append({"source": state.pdf_path, "field": "full_text", "text": result.full_text[:5000]})

    for attr_name, pattern in SPEC_PATTERNS.items():
        match = pattern.search(result.full_text)
        if not match:
            continue
        raw_value = match.group(1)
        unit = match.group(2) if match.lastindex and match.lastindex >= 2 else None

        page, evidence = find_snippet_page(result, match.group(0))

        value: float | str
        try:
            value = float(raw_value.replace(",", ""))
        except ValueError:
            value = raw_value

        state.attributes[attr_name] = AttributeValue(
            value=value,
            unit=unit,
            confidence=0.9,
            source=state.pdf_path,
            source_type=SourceType.PDF,
            page=page,
            evidence=evidence or match.group(0),
            method=ExtractionMethod.PDF_EXTRACTION,
            status=AttributeStatus.EXTRACTED,
        )


def _from_image(state: ProductState) -> None:
    if not state.image_path:
        return
    result = analyze_image(state.image_path)
    if not result.get("success"):
        state.log("discovery_agent", "image_analysis_failed", result.get("error"))
        return

    state.raw_extractions.append({"source": state.image_path, "field": "vision_analysis", "text": str(result)})

    if result.get("product_type") and result["product_type"] != "unknown":
        state.attributes.setdefault(
            "product_type_visual",
            AttributeValue(
                value=result["product_type"],
                confidence=min(0.7, float(result.get("confidence", 0.5))),
                source=state.image_path,
                source_type=SourceType.IMAGE,
                evidence=", ".join(result.get("visible_labels", [])) or None,
                method=ExtractionMethod.IMAGE_ANALYSIS,
                status=AttributeStatus.EXTRACTED,
            ),
        )

    for i, label in enumerate(result.get("visible_labels", [])):
        state.attributes[f"visible_label_{i+1}"] = AttributeValue(
            value=label,
            confidence=0.6,
            source=state.image_path,
            source_type=SourceType.IMAGE,
            evidence=label,
            method=ExtractionMethod.IMAGE_ANALYSIS,
            status=AttributeStatus.EXTRACTED,
        )


def run(state: ProductState) -> ProductState:
    _from_user_input(state)
    _from_pdf(state)
    _from_image(state)
    state.log("discovery_agent", "completed", f"{len(state.attributes)} attributes extracted")
    return state
