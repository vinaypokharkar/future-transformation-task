"""PDFs containing images.

Three cases, and only two of them were handled before:
  A. image-only (a true scan)          -> extracts nothing
  B. text + images (an ordinary PDF)   -> extracts the text, ignores the images
  C. mostly image + a page number      -> extracts "3": not empty, not useful
"""

import io
import zlib
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.ai import extractor

P = settings.api_prefix
SAMPLE_PDF = Path(__file__).resolve().parents[2] / "sample_docs" / "onboarding_guide.pdf"


def _build_pdf(builder) -> bytes:
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    catalog_id, _ = builder(add)

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, catalog_id, xref,
    )
    return bytes(out)


def _image_xobject(add, shade: int) -> int:
    raw = zlib.compress(bytes([shade, shade, shade] * 16))
    return add(
        b"<< /Type /XObject /Subtype /Image /Width 4 /Height 4 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
        b"/Length %d >>\nstream\n%s\nendstream" % (len(raw), raw)
    )


def image_only_pdf() -> bytes:
    """A page whose entire content is a drawn image. No text operators."""
    def build(add):
        img_id = _image_xobject(add, 200)
        content = b"q 400 0 0 400 100 300 cm /Im0 Do Q"
        content_id = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content))
        pages_id = 4
        page_id = add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /XObject << /Im0 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_id, img_id, content_id)
        )
        add(b"<< /Type /Pages /Kids [%d 0 R] /Count 1 >>" % page_id)
        return add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id), pages_id
    return _build_pdf(build)


def scanned_pdf_with_page_number() -> bytes:
    """What a real scan looks like: images, plus a text layer holding "3"."""
    def build(add):
        img_id = _image_xobject(add, 180)
        font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        content = b"q 400 0 0 400 100 300 cm /Im0 Do Q\nBT /F1 9 Tf 300 50 Td (3) Tj ET"
        content_id = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content))
        pages_id = 5
        page_id = add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /XObject << /Im0 %d 0 R >> /Font << /F1 %d 0 R >> >> "
            b"/Contents %d 0 R >>" % (pages_id, img_id, font_id, content_id)
        )
        add(b"<< /Type /Pages /Kids [%d 0 R] /Count 1 >>" % page_id)
        return add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id), pages_id
    return _build_pdf(build)


def test_image_only_pdf_rejected(client, admin_headers):
    """Case A: extracts nothing at all."""
    r = client.post(
        f"{P}/documents",
        headers=admin_headers,
        files={"file": ("scan.pdf", io.BytesIO(image_only_pdf()), "application/pdf")},
    )
    assert r.status_code == 422
    assert "no text" in r.json()["detail"].lower()


def test_scanned_pdf_with_only_a_page_number_rejected(client, admin_headers):
    """Case C: the one that used to slip through.

    Extraction returns "3", which is not empty, so the document was accepted,
    marked 'indexed' with chunk_count=1, and a vector for "3" entered the index.
    The user saw 'indexed' and believed the file was searchable; none of its
    real content was.
    """
    r = client.post(
        f"{P}/documents",
        headers=admin_headers,
        files={"file": ("scan.pdf", io.BytesIO(scanned_pdf_with_page_number()), "application/pdf")},
    )
    assert r.status_code == 422
    detail = r.json()["detail"].lower()
    assert "almost no extractable text" in detail
    assert "scan" in detail


def test_real_text_pdf_still_accepted(client, admin_headers):
    """The density rule must not reject genuine documents."""
    if not SAMPLE_PDF.exists():
        pytest.skip("sample PDF not generated; run scripts/make_sample_pdf.py")
    with open(SAMPLE_PDF, "rb") as fh:
        r = client.post(
            f"{P}/documents",
            headers=admin_headers,
            files={"file": (SAMPLE_PDF.name, fh, "application/pdf")},
        )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "indexed"
    assert body["chunk_count"] > 1


def test_short_txt_still_accepted(client, admin_headers):
    """Density is a PDF rule only.

    A 21-character note is legitimate content; applying a length floor to .txt
    would reject real documents to fix a PDF problem.
    """
    r = client.post(
        f"{P}/documents",
        headers=admin_headers,
        files={"file": ("note.txt", io.BytesIO(b"Office closed Dec 25."), "text/plain")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "indexed"


def test_density_threshold_separates_real_from_scanned():
    """The threshold is measured, not guessed.

    Real PDFs in this repo extract 675-775 chars/page; a scan's text layer
    carries a handful. 100 sits far from both.
    """
    assert extractor.is_pdf_text_too_sparse("3", page_count=1) is True
    assert extractor.is_pdf_text_too_sparse("x" * 20, page_count=1) is True
    # A real document's density, by a wide margin.
    assert extractor.is_pdf_text_too_sparse("x" * 775, page_count=1) is False
    assert extractor.is_pdf_text_too_sparse("x" * 1549, page_count=2) is False
    # Page count must divide: 300 chars is fine on one page, sparse across ten.
    assert extractor.is_pdf_text_too_sparse("x" * 300, page_count=1) is False
    assert extractor.is_pdf_text_too_sparse("x" * 300, page_count=10) is True


def test_unknown_page_count_does_not_reject():
    """A page count of 0 means counting failed, which is not evidence of a scan."""
    assert extractor.is_pdf_text_too_sparse("3", page_count=0) is False
