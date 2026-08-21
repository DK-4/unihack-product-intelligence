import fitz  # PyMuPDF

from services.pdf_service import extract_pdf, find_snippet_page


def test_missing_pdf_fails_gracefully():
    result = extract_pdf("does_not_exist.pdf")
    assert result.success is False
    assert "not found" in result.error.lower()


def test_extract_real_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Motor power: 5.5 kW")
    page.insert_text((72, 100), "Maximum pressure: 10 bar")
    doc.save(str(pdf_path))
    doc.close()

    result = extract_pdf(str(pdf_path))
    assert result.success is True
    assert len(result.pages) == 1
    assert "5.5" in result.full_text

    page_num, snippet = find_snippet_page(result, "Motor power: 5.5 kW")
    assert page_num == 1
    assert "5.5" in snippet


def test_empty_pdf_fails_gracefully(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    result = extract_pdf(str(pdf_path))
    assert result.success is False
