"""Generate the sample onboarding PDF.

A text-based PDF, deliberately: a scanned/image PDF extracts to nothing and
would exercise the failure path rather than the demo path.

Uses pypdf, which is already a dependency, rather than adding reportlab for one
fixture. Writes raw PDF content streams — verbose, but no new package.

Usage (from backend/, venv activated):
    python -m scripts.make_sample_pdf
"""

import zlib
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[2] / "sample_docs" / "onboarding_guide.pdf"

PAGES: list[list[str]] = [
    [
        "Acme Corporation - New Starter Onboarding Guide",
        "",
        "Welcome",
        "",
        "This guide covers your first two weeks at Acme. Your manager will walk",
        "through it with you on day one.",
        "",
        "Day One",
        "",
        "Collect your laptop and access badge from the reception desk. Your",
        "accounts are created in advance, and your temporary password is sent to",
        "your personal email address the working day before you start.",
        "",
        "You must change that temporary password on first sign-in, and enrol in",
        "multi-factor authentication before you can reach any internal system.",
        "",
        "Probation",
        "",
        "New employees serve a probation period of six months. Your manager will",
        "hold a formal review at the three month mark and again before probation",
        "ends. Probation may be extended once, by up to three months.",
    ],
    [
        "Holiday and Time Off",
        "",
        "Full-time staff receive 25 days of paid annual leave, in addition to",
        "public holidays. Leave accrues monthly and unused days do not carry over",
        "into the following year beyond a maximum of five days.",
        "",
        "Requests must be submitted at least two weeks in advance through the HR",
        "portal, and require manager approval before travel is booked.",
        "",
        "Working Hours",
        "",
        "Core hours are 10:00 to 16:00. Outside core hours, staff may start and",
        "finish at times that suit them, provided their contracted weekly hours",
        "are met and meetings are honoured.",
        "",
        "Remote Work",
        "",
        "Staff may work remotely up to three days per week. Fully remote",
        "arrangements require director approval and are reviewed annually.",
        "",
        "Support",
        "",
        "IT support is reachable through the internal helpdesk. For anything",
        "related to pay or contracts, contact the people team directly.",
    ],
]


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(lines: list[str]) -> bytes:
    parts = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
    for line in lines:
        parts.append(f"({_escape(line)}) Tj")
        parts.append("T*")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1")


def build_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_ids: list[int] = []
    content_ids: list[int] = []
    for lines in pages:
        stream = zlib.compress(_content_stream(lines))
        content_ids.append(
            add(
                b"<< /Length %d /Filter /FlateDecode >>\nstream\n%s\nendstream"
                % (len(stream), stream)
            )
        )

    pages_id = len(objects) + len(pages) + 1
    for content_id in content_ids:
        page_ids.append(
            add(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                % (pages_id, font_id, content_id)
            )
        )

    kids = b" ".join(b"%d 0 R" % pid for pid in page_ids)
    add(b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids)))
    catalog_id = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog_id,
        xref_pos,
    )
    return bytes(out)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(build_pdf(PAGES))

    # Verify with the same library the upload path uses. A fixture that pypdf
    # cannot read is worse than no fixture — it would fail the demo, not the
    # generator.
    from pypdf import PdfReader

    reader = PdfReader(str(OUTPUT))
    extracted = "\n".join(p.extract_text() or "" for p in reader.pages)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes, {len(reader.pages)} pages)")
    print(f"pypdf extracted {len(extracted)} characters")
    if len(extracted.strip()) < 200:
        raise SystemExit("PDF text extraction produced too little text")
    print("Extraction verified")


if __name__ == "__main__":
    main()
