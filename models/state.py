"""
ProductState: the single shared object that flows through the whole
agent pipeline (Discovery -> Standardization -> Enrichment -> Trust).

Each agent reads from and writes to this same object instead of
inventing its own ad-hoc output format. This keeps the pipeline
composable and makes every stage independently testable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.product import AttributeValue, ValidationSummary


class ProductIdentity(BaseModel):
    part_number: str
    brand: str
    description: str
    product_name: Optional[str] = None


class Classification(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    family: Optional[str] = None
    confidence: float = 0.0


class ProcessingLogEntry(BaseModel):
    agent: str
    action: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    detail: Optional[str] = None


class ProductState(BaseModel):
    # --- identity & inputs ---
    product_identity: ProductIdentity
    pdf_path: Optional[str] = None
    image_path: Optional[str] = None
    product_url: Optional[str] = None

    # --- pipeline outputs ---
    classification: Classification = Field(default_factory=Classification)
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)
    applications: dict[str, AttributeValue] = Field(default_factory=dict)
    description_enriched: Optional[AttributeValue] = None

    # --- raw intermediate evidence from Agent 1 (kept for traceability) ---
    raw_extractions: list[dict] = Field(default_factory=list)

    # --- validation ---
    validation: ValidationSummary = Field(default_factory=ValidationSummary)

    # --- bookkeeping ---
    processing_log: list[ProcessingLogEntry] = Field(default_factory=list)
    human_review_required: bool = False

    def log(self, agent: str, action: str, detail: Optional[str] = None) -> None:
        self.processing_log.append(ProcessingLogEntry(agent=agent, action=action, detail=detail))

    def to_final_json(self) -> dict:
        """Final export shape matching the challenge's expected output format."""
        return {
            "product_name": self.product_identity.product_name
            or f"{self.product_identity.part_number} {self.product_identity.description}".strip(),
            "manufacturer": self.product_identity.brand,
            "category": self.classification.category,
            "subcategory": self.classification.subcategory,
            "attributes": {k: v.model_dump() for k, v in self.attributes.items()},
            "applications": {k: v.model_dump() for k, v in self.applications.items()},
            "description": self.description_enriched.model_dump() if self.description_enriched else None,
            "validation": self.validation.model_dump(),
            "human_review_required": self.human_review_required,
            "processing_log": [p.model_dump() for p in self.processing_log],
        }
