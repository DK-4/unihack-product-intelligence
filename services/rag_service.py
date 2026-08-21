"""
Minimal RAG service.

Documents / Trusted Sources -> Chunking -> Embeddings -> Vector DB (Chroma)
-> Similarity Search -> Retrieved Evidence -> Enrichment Agent

Deliberately simple: local, on-disk Chroma collection built from
data/knowledge_base/*.txt (or .md). If Chroma or the embedding function
is unavailable, retrieval degrades to a naive keyword search over the
same files so enrichment never hard-crashes.
"""

from __future__ import annotations

import glob
import os

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge_base")
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_store")


def _load_kb_documents() -> list[tuple[str, str]]:
    """Returns [(filename, content), ...] for every .txt/.md file in the knowledge base."""
    docs = []
    for path in glob.glob(os.path.join(KB_DIR, "*")):
        if path.lower().endswith((".txt", ".md")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    docs.append((os.path.basename(path), f.read()))
            except Exception:
                continue
    return docs


def _chunk(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += size - overlap
    return chunks


class RagService:
    def __init__(self):
        self._collection = None
        self._fallback_docs: list[tuple[str, str]] | None = None
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            os.makedirs(CHROMA_DIR, exist_ok=True)
            client = chromadb.PersistentClient(path=CHROMA_DIR)
            ef = embedding_functions.DefaultEmbeddingFunction()
            self._collection = client.get_or_create_collection("unihack_kb", embedding_function=ef)

            docs = _load_kb_documents()
            existing = self._collection.count()
            if existing == 0 and docs:
                ids, texts, metas = [], [], []
                for fname, content in docs:
                    for i, chunk in enumerate(_chunk(content)):
                        ids.append(f"{fname}::{i}")
                        texts.append(chunk)
                        metas.append({"source": fname})
                if ids:
                    self._collection.add(ids=ids, documents=texts, metadatas=metas)
        except Exception:
            self._collection = None
            self._fallback_docs = _load_kb_documents()

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """Returns [{text, source, score}, ...]"""
        if self._collection is not None:
            try:
                res = self._collection.query(query_texts=[query], n_results=top_k)
                out = []
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                dists = res.get("distances", [[]])[0] if res.get("distances") else [None] * len(docs)
                for doc, meta, dist in zip(docs, metas, dists):
                    score = None if dist is None else max(0.0, 1.0 - dist)
                    out.append({"text": doc, "source": meta.get("source", "knowledge_base"), "score": score})
                return out
            except Exception:
                pass  # fall through to naive search

        # naive fallback: keyword overlap search
        docs = self._fallback_docs if self._fallback_docs is not None else _load_kb_documents()
        query_terms = set(query.lower().split())
        scored = []
        for fname, content in docs:
            for chunk in _chunk(content):
                overlap = len(query_terms & set(chunk.lower().split()))
                if overlap > 0:
                    scored.append({"text": chunk, "source": fname, "score": overlap})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


_rag_singleton: RagService | None = None


def get_rag_service() -> RagService:
    global _rag_singleton
    if _rag_singleton is None:
        _rag_singleton = RagService()
    return _rag_singleton
