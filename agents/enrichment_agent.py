"""
AGENT 3 - Enrichment

Adds intelligence that wasn't explicitly present in the raw inputs:
applications, a search-friendly description, related terminology. Uses
RAG retrieval over data/knowledge_base as grounding, then an LLM call
to synthesize -- everything produced here is explicitly tagged as
ENRICHED (not verified/extracted), per the "never present assumptions
as verified facts" principle.
"""

from __future__ import annotations

from models.product import AttributeStatus, AttributeValue, ExtractionMethod, SourceType
from models.state import ProductState
from services.llm_service import get_llm_client
from services.rag_service import get_rag_service

ENRICHMENT_SYSTEM_PROMPT = """You are an industrial-product enrichment assistant.
Given a product's classification, known attributes, and retrieved reference
snippets, propose likely APPLICATIONS and a short marketing-style DESCRIPTION.
Only use the retrieved snippets and given attributes as grounding -- do not
invent numeric specifications. Return strict JSON:
{
  "applications": ["...", "..."],
  "description": "one or two sentence product description",
  "confidence": 0.0-1.0
}
"""


def run(state: ProductState) -> ProductState:
    rag = get_rag_service()
    query = f"{state.classification.family or state.classification.subcategory or ''} {state.product_identity.description}"
    retrieved = rag.retrieve(query, top_k=3)

    known_attrs = ", ".join(f"{k}={v.value}{v.unit or ''}" for k, v in state.attributes.items())
    context = "\n".join(f"- ({r['source']}): {r['text'][:300]}" for r in retrieved) or "(no relevant reference material found)"

    client = get_llm_client()
    prompt = (
        f"Product: {state.product_identity.description}\n"
        f"Category: {state.classification.category} / {state.classification.subcategory}\n"
        f"Known attributes: {known_attrs}\n"
        f"Retrieved reference snippets:\n{context}\n"
    )
    try:
        result = client.json(ENRICHMENT_SYSTEM_PROMPT, prompt)
    except Exception:
        result = {}

    if result.get("mock") or not result.get("applications"):
        # offline fallback grounded only in what we already know / retrieved
        fallback_apps = [r["source"].replace("_", " ").replace(".txt", "") for r in retrieved[:2]] or ["General Industrial Use"]
        result = {
            "applications": fallback_apps,
            "description": f"{state.product_identity.description} by {state.product_identity.brand}.",
            "confidence": 0.4 if retrieved else 0.25,
        }

    conf = float(result.get("confidence", 0.5))
    source_label = "retrieved_knowledge" if retrieved else "llm_reasoning"
    source_type = SourceType.RETRIEVED_KNOWLEDGE if retrieved else SourceType.LLM_REASONING

    for i, app in enumerate(result.get("applications", [])):
        state.applications[f"application_{i+1}"] = AttributeValue(
            value=app,
            confidence=conf,
            source=source_label,
            source_type=source_type,
            evidence="; ".join(r["text"][:120] for r in retrieved) or None,
            method=ExtractionMethod.ENRICHMENT,
            status=AttributeStatus.ENRICHED,
        )

    if result.get("description"):
        state.description_enriched = AttributeValue(
            value=result["description"],
            confidence=conf,
            source=source_label,
            source_type=source_type,
            method=ExtractionMethod.ENRICHMENT,
            status=AttributeStatus.ENRICHED,
        )

    state.log("enrichment_agent", "completed", f"{len(result.get('applications', []))} applications enriched")
    return state
