"""
FastAPI entrypoint for UniHack Product Intelligence.

Run with:
    uvicorn main:app --reload

Endpoints:
    POST /generate       - run the full pipeline for one product
    GET  /products        - list processed products (SQLite-backed)
    GET  /products/{id}   - fetch one product's full traceable record
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from models.state import ProductIdentity, ProductState
from orchestrator import run_pipeline

DB_PATH = os.getenv("DB_PATH", "unihack.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/sample_products")

app = FastAPI(title="UniHack Product Intelligence API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                part_number TEXT,
                brand TEXT,
                record_json TEXT
            )"""
        )
        yield conn
        conn.commit()
    finally:
        conn.close()


@app.on_event("startup")
def _init_db():
    with get_db():
        pass


def _save_upload(upload: Optional[UploadFile]) -> Optional[str]:
    if upload is None or not upload.filename:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{upload.filename}")
    with open(dest, "wb") as f:
        f.write(upload.file.read())
    return dest


@app.post("/generate")
async def generate_product_intelligence(
    part_number: str = Form(...),
    brand: str = Form(...),
    description: str = Form(...),
    product_url: Optional[str] = Form(None),
    pdf: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
):
    try:
        pdf_path = _save_upload(pdf)
        image_path = _save_upload(image)

        state = ProductState(
            product_identity=ProductIdentity(part_number=part_number, brand=brand, description=description),
            pdf_path=pdf_path,
            image_path=image_path,
            product_url=product_url,
        )
        final_state = run_pipeline(state)
        record = final_state.to_final_json()

        product_id = uuid.uuid4().hex
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, part_number, brand, record_json) VALUES (?, ?, ?, ?)",
                (product_id, part_number, brand, json.dumps(record)),
            )

        return {"id": product_id, **record}
    except Exception as e:  # noqa: BLE001 - top-level safety net; one bad product must not crash the app
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}") from e


@app.get("/products")
def list_products():
    with get_db() as conn:
        rows = conn.execute("SELECT id, part_number, brand FROM products").fetchall()
    return [{"id": r[0], "part_number": r[1], "brand": r[2]} for r in rows]


@app.get("/products/{product_id}")
def get_product(product_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT record_json FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return json.loads(row[0])


@app.get("/health")
def health():
    return {"status": "ok"}
