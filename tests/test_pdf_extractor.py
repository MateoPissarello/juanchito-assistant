from pathlib import Path
import pytest

from juanchito_assitant.ingest.pdf_extractor import extract_text_from_pdf


def test_extract_text_from_pdf_success():
    pdf_path = Path("data/linkedin_profile.pdf")
    if not pdf_path.exists():
        pytest.skip("data/linkedin_profile.pdf no encontrado.")

    text = extract_text_from_pdf(pdf_path)
    assert isinstance(text, str)
    assert len(text) > 100
    assert "Mateo Pissarello" in text
    assert "Icebergdata" in text


def test_extract_text_from_pdf_nonexistent():
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("data/non_existent_file.pdf")
