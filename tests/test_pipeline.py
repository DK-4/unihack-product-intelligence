import fitz

from models.state import ProductIdentity, ProductState
from orchestrator import run_pipeline


def _make_sample_pdf(tmp_path):
    pdf_path = tmp_path / "X200_datasheet.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Motor Power: 5.5 kW")
    page.insert_text((72, 100), "Flow Rate: 120 m3/h")
    page.insert_text((72, 130), "Maximum Pressure: 10 bar")
    page.insert_text((72, 160), "Material: Stainless Steel")
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_end_to_end_pipeline_minimal_input():
    """Minimal input only (no PDF/image) -- pipeline must still complete without crashing."""
    state = ProductState(
        product_identity=ProductIdentity(part_number="X200", brand="ABC Industries", description="Industrial centrifugal pump")
    )
    result = run_pipeline(state)
    assert result.classification.category is not None
    assert result.validation is not None
    assert len(result.processing_log) == 4  # one entry per agent


def test_end_to_end_pipeline_with_pdf(tmp_path):
    pdf_path = _make_sample_pdf(tmp_path)
    state = ProductState(
        product_identity=ProductIdentity(part_number="X200", brand="ABC Industries", description="Industrial centrifugal pump"),
        pdf_path=pdf_path,
    )
    result = run_pipeline(state)
    record = result.to_final_json()

    assert "power" in record["attributes"]
    assert record["attributes"]["power"]["value"] == 5.5
    assert record["attributes"]["power"]["source"] == pdf_path
    assert record["validation"]["trust_score"] >= 0.0


def test_pipeline_handles_bad_pdf_gracefully(tmp_path):
    bad_pdf = tmp_path / "corrupt.pdf"
    bad_pdf.write_text("not a real pdf")
    state = ProductState(
        product_identity=ProductIdentity(part_number="X1", brand="Brand", description="widget"),
        pdf_path=str(bad_pdf),
    )
    # must not raise
    result = run_pipeline(state)
    assert result is not None
