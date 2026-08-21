"""
Core traceable data primitives for UniHack Product Intelligence.

Every meaningful piece of product data is wrapped in an AttributeValue,
which carries value + unit + confidence + source + evidence + method +
status. This is the "evidence-first" backbone of the whole system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    USER_INPUT = "user_input"
    PDF = "pdf"
    IMAGE = "image"
    URL = "url"
    RETRIEVED_KNOWLEDGE = "retrieved_knowledge"
    LLM_REASONING = "llm_reasoning"
    RULE = "rule"


class ExtractionMethod(str, Enum):
    DIRECT_INPUT = "direct_input"
    PDF_EXTRACTION = "pdf_extraction"
    IMAGE_ANALYSIS = "image_analysis"
    NORMALIZATION = "normalization"
    ENRICHMENT = "enrichment"
    LLM_INFERENCE = "llm_inference"
    RULE_BASED = "rule_based"


class AttributeStatus(str, Enum):
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    ENRICHED = "enriched"
    INFERRED = "inferred"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    CONFLICT = "conflict"
    REJECTED = "rejected"
    APPROVED = "approved"


class AttributeValue(BaseModel):
    """A single traceable fact about a product."""

    value: Any = Field(..., description="The extracted/derived value. Use 'unknown' if unavailable.")
    unit: Optional[str] = None
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    source: Optional[str] = Field(None, description="Filename / URL / origin identifier")
    source_type: Optional[SourceType] = None
    page: Optional[int] = Field(None, description="Page number, when applicable (PDF)")
    section: Optional[str] = None
    evidence: Optional[str] = Field(None, description="Verbatim-ish snippet supporting the value")
    method: Optional[ExtractionMethod] = None
    status: AttributeStatus = AttributeStatus.EXTRACTED
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class Conflict(BaseModel):
    attribute: str
    values: list[dict] = Field(default_factory=list, description="[{source, value, unit}, ...]")
    description: str
    status: str = "needs_review"


class ValidationSummary(BaseModel):
    trust_score: float = Field(0.0, ge=0.0, le=1.0)
    verified_count: int = 0
    needs_review_count: int = 0
    conflict_count: int = 0
    conflicts: list[Conflict] = Field(default_factory=list)
    rule_failures: list[str] = Field(default_factory=list)
