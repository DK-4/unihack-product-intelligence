"""
Vision / image-understanding service.

Sends a product image to a multimodal LLM (via llm_service) and asks
for ONLY what is visually verifiable: product type/family, visible
labels/model numbers, and obvious physical characteristics. The prompt
explicitly forbids inventing specs that can't be seen.
"""

from __future__ import annotations

import base64
import os

from services.llm_service import get_llm_client

VISION_SYSTEM_PROMPT = """You are a product-image analyst for industrial equipment.
Look ONLY at what is visibly present in the image. Do not guess technical
specifications (power, flow rate, pressure, etc.) that cannot be read directly
off a label in the image. If something is not visible, omit it or say "unknown".

Return strict JSON with this shape:
{
  "product_type": "string or unknown",
  "visible_labels": ["any text/model numbers you can actually read"],
  "physical_characteristics": ["short observations, e.g. 'stainless steel housing'"],
  "confidence": 0.0-1.0
}
"""


def analyze_image(image_path: str) -> dict:
    if not image_path or not os.path.exists(image_path):
        return {"success": False, "error": f"Image not found: {image_path}"}

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        media_type = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"Failed to read image: {e}"}

    client = get_llm_client()
    try:
        result = client.vision_json(
            system_prompt=VISION_SYSTEM_PROMPT,
            image_b64=b64,
            media_type=media_type,
            user_prompt="Analyze this industrial product image.",
        )
        result["success"] = True
        return result
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"Vision analysis failed: {e}"}
