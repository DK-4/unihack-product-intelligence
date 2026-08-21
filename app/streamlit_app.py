"""
UniHack Product Intelligence -- Streamlit dashboard.

Run with:
    streamlit run app/streamlit_app.py

This talks directly to the pipeline in-process (no need to run the
FastAPI server separately for the demo), so it works standalone.
"""

from __future__ import annotations

import os
import sys
import tempfile

import json
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.state import ProductIdentity, ProductState  # noqa: E402
from orchestrator import run_pipeline  # noqa: E402

st.set_page_config(page_title="UniHack Product Intelligence", layout="wide")

st.title("🏭 UniHack — AI Product Intelligence for Industrial Commerce")
st.caption("Limited input → Discovery → Standardization → Enrichment → Trust/Validation → Traceable record")

with st.sidebar:
    st.header("Product Input")
    part_number = st.text_input("Part Number", value="X200")
    brand = st.text_input("Brand / Manufacturer", value="ABC Industries")
    description = st.text_area("Short Description", value="Industrial centrifugal pump")
    product_url = st.text_input("Product URL (optional)")
    pdf_file = st.file_uploader("Datasheet PDF (optional)", type=["pdf"])
    image_file = st.file_uploader("Product Image (optional)", type=["jpg", "jpeg", "png"])
    generate = st.button("🚀 Generate Product Intelligence", type="primary", use_container_width=True)

if "state" not in st.session_state:
    st.session_state.state = None

if generate:
    if not part_number or not brand or not description:
        st.error("Part number, brand, and description are required.")
    else:
        pdf_path = None
        image_path = None
        if pdf_file is not None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(pdf_file.read())
            tmp.close()
            pdf_path = tmp.name
        if image_file is not None:
            suffix = os.path.splitext(image_file.name)[1] or ".jpg"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(image_file.read())
            tmp.close()
            image_path = tmp.name

        state = ProductState(
            product_identity=ProductIdentity(part_number=part_number, brand=brand, description=description),
            pdf_path=pdf_path,
            image_path=image_path,
            product_url=product_url or None,
        )

        status = st.status("Running 4-agent pipeline...", expanded=True)
        try:
            status.write("Running Discovery, Standardization, Enrichment, Trust agents...")
            final_state = run_pipeline(state)
            for entry in final_state.processing_log:
                status.write(f"✓ **{entry.agent}** — {entry.action} ({entry.detail or ''})")
            status.update(label="Pipeline completed", state="complete")
            st.session_state.state = final_state
        except Exception as e:  # noqa: BLE001
            status.update(label="Pipeline failed", state="error")
            st.exception(e)

state: ProductState | None = st.session_state.state

if state is not None:
    record = state.to_final_json()

    st.subheader(record["product_name"] or "Unnamed product")
    col1, col2, col3 = st.columns(3)
    col1.metric("Manufacturer", record["manufacturer"] or "unknown")
    col2.metric("Category", record["category"] or "unknown")
    col3.metric("Subcategory", record["subcategory"] or "unknown")

    v = record["validation"]
    st.markdown("### 🛡️ Validation")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Trust Score", f"{v['trust_score']*100:.0f}%")
    m2.metric("Verified", v["verified_count"])
    m3.metric("Needs Review", v["needs_review_count"])
    m4.metric("Conflicts", v["conflict_count"])
    if v["rule_failures"]:
        st.warning("Rule failures:\n" + "\n".join(f"- {f}" for f in v["rule_failures"]))
    if state.human_review_required:
        st.info("⚠️ This record has items flagged for human review below.")

    st.markdown("### 📋 Specifications")
    spec_rows = []
    for name, attr in record["attributes"].items():
        spec_rows.append(
            {
                "Attribute": name,
                "Value": attr["value"],
                "Unit": attr.get("unit") or "",
                "Confidence": f"{attr['confidence']*100:.0f}%",
                "Status": attr["status"],
                "Source": attr.get("source") or "",
                "Page": attr.get("page") or "",
            }
        )
    if spec_rows:
        df = pd.DataFrame(spec_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        with st.expander("🔎 Inspect evidence for an attribute"):
            chosen = st.selectbox("Attribute", list(record["attributes"].keys()))
            attr = record["attributes"][chosen]
            st.json(attr)
    else:
        st.info("No structured attributes extracted yet -- try uploading a datasheet PDF.")

    st.markdown("### ✨ Enrichment")
    if record["description"]:
        st.write(f"**Description:** {record['description']['value']}  \n"
                  f"*(confidence {record['description']['confidence']*100:.0f}%, status: {record['description']['status']})*")
    apps = record["applications"]
    if apps:
        for name, a in apps.items():
            st.write(f"- {a['value']}  ·  confidence {a['confidence']*100:.0f}%  ·  status: `{a['status']}`")
    else:
        st.caption("No applications enriched.")

    if state.human_review_required:
        st.markdown("### 🧑‍⚖️ Human Review")
        for name, attr in state.attributes.items():
            if attr.status == "needs_review":
                cols = st.columns([3, 2, 2, 2])
                cols[0].write(f"**{name}**: {attr.value} {attr.unit or ''}")
                if cols[1].button("Approve", key=f"approve_{name}"):
                    attr.status = "approved"
                    st.rerun()
                if cols[2].button("Reject", key=f"reject_{name}"):
                    attr.status = "rejected"
                    st.rerun()
                cols[3].caption(f"confidence {attr.confidence*100:.0f}%")

    st.markdown("### 📤 Export")
    st.download_button(
        "Download JSON",
       data=json.dumps(record, indent=2, default=str),
        file_name=f"{record['product_name'] or 'product'}.json".replace(" ", "_"),
        mime="application/json",
    )
else:
    st.info("Fill in the product details in the sidebar and click **Generate Product Intelligence** to begin.")
