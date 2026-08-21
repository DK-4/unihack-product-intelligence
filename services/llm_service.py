"""
LLM service abstraction.

Reads MODEL_PROVIDER from the environment ("openai" | "gemini" | "mock")
and exposes a small, uniform interface:

    client.json(system_prompt, user_prompt) -> dict
    client.vision_json(system_prompt, image_b64, media_type, user_prompt) -> dict

If no API key is configured, the service transparently falls back to a
deterministic "mock" mode so the whole pipeline stays runnable for demo
/ offline / no-budget scenarios (per the error-handling requirement:
missing API key must never crash the app).
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()


def _strip_code_fences(text: str) -> str:
    return re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()


class BaseLLMClient(ABC):
    @abstractmethod
    def json(self, system_prompt: str, user_prompt: str) -> dict: ...

    @abstractmethod
    def vision_json(self, system_prompt: str, image_b64: str, media_type: str, user_prompt: str) -> dict: ...


class MockLLMClient(BaseLLMClient):
    """Deterministic offline fallback. No hallucinated specs -- returns
    conservative/empty structures so downstream agents degrade gracefully."""

    def json(self, system_prompt: str, user_prompt: str) -> dict:
        return {"mock": True, "note": "No LLM API key configured; returning empty structured result."}

    def vision_json(self, system_prompt: str, image_b64: str, media_type: str, user_prompt: str) -> dict:
        return {
            "product_type": "unknown",
            "visible_labels": [],
            "physical_characteristics": [],
            "confidence": 0.0,
            "mock": True,
        }


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI  # imported lazily so the package is optional

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def json(self, system_prompt: str, user_prompt: str) -> dict:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)

    def vision_json(self, system_prompt: str, image_b64: str, media_type: str, user_prompt: str) -> dict:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai  # imported lazily, optional dependency

        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    def json(self, system_prompt: str, user_prompt: str) -> dict:
        model = self._genai.GenerativeModel(self._model_name, system_instruction=system_prompt)
        resp = model.generate_content(user_prompt)
        return json.loads(_strip_code_fences(resp.text))

    def vision_json(self, system_prompt: str, image_b64: str, media_type: str, user_prompt: str) -> dict:
        import base64

        model = self._genai.GenerativeModel(self._model_name, system_instruction=system_prompt)
        image_bytes = base64.b64decode(image_b64)
        resp = model.generate_content(
            [user_prompt, {"mime_type": media_type, "data": image_bytes}]
        )
        return json.loads(_strip_code_fences(resp.text))


_client_singleton: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton

    provider = os.getenv("MODEL_PROVIDER", "mock").lower()

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            _client_singleton = OpenAIClient(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            )
            return _client_singleton
        except Exception:
            pass  # fall through to mock

    if provider == "gemini" and os.getenv("GEMINI_API_KEY"):
        try:
            _client_singleton = GeminiClient(
                api_key=os.getenv("GEMINI_API_KEY"),
                model=os.getenv("MODEL_NAME", "gemini-1.5-flash"),
            )
            return _client_singleton
        except Exception:
            pass  # fall through to mock

    _client_singleton = MockLLMClient()
    return _client_singleton
