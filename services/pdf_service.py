"""
PDF document intelligence service.

Extracts text, tables (best-effort), and page-indexed content from a
datasheet PDF using PyMuPDF (fitz). Designed to fail gracefully: a
missing/corrupt/empty PDF never crashes the pipeline, it just yields
no evidence.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class PageContent:
    page_number: int  # 1-indexed
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)


@dataclass
class PdfExtractionResult:
    success: bool
    pages: list[PageContent] = field(default_factory=list)
    error: str | None = None

    @property
    def full_text(self) -> str:
        return "\n".join(f"[page {p.page_number}]\n{p.text}" for p in self.pages)


def extract_pdf(path: str) -> PdfExtractionResult:
    if not path or not os.path.exists(path):
        return PdfExtractionResult(success=False, error=f"PDF not found: {path}")

    try:
        import fitz  # PyMuPDF
    except ImportError:
        return PdfExtractionResult(success=False, error="PyMuPDF (fitz) is not installed")

    try:
        doc = fitz.open(path)
    except Exception as e:  # noqa: BLE001 - want to surface any fitz error as a graceful failure
        return PdfExtractionResult(success=False, error=f"Failed to open PDF: {e}")

    if doc.page_count == 0:
        return PdfExtractionResult(success=False, error="PDF has no pages")

    pages: list[PageContent] = []
    try:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            tables: list[list[list[str]]] = []
            try:
                finder = page.find_tables()
                for t in finder.tables:
                    tables.append(t.extract())
            except Exception:
                # table extraction is best-effort; older PyMuPDF versions
                # or malformed pages should not break the pipeline
                pass
            pages.append(PageContent(page_number=i, text=text, tables=tables))
    finally:
        doc.close()

    if all(not p.text.strip() for p in pages):
        return PdfExtractionResult(success=False, error="PDF appears to be empty or scanned (no extractable text)")

    return PdfExtractionResult(success=True, pages=pages)


def find_snippet_page(result: PdfExtractionResult, needle: str) -> tuple[int | None, str | None]:
    """Locate which page (and a short evidence snippet) contains `needle` (case-insensitive)."""
    needle_lower = needle.lower().strip()
    if not needle_lower:
        return None, None
    for page in result.pages:
        idx = page.text.lower().find(needle_lower)
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(page.text), idx + len(needle_lower) + 40)
            snippet = page.text[start:end].replace("\n", " ").strip()
            return page.page_number, snippet
    return None, None
