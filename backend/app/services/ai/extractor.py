import logging
from pathlib import Path

from app.core.exceptions import ValidationError
from app.models.document import FileType

logger = logging.getLogger(__name__)

# Below this many characters per page, a PDF is a scan rather than a document.
#
# Measured, not guessed. Real text PDFs in this repo extract 675-775 chars/page
# (onboarding_guide.pdf: 774.5, the assignment brief: 675.5). A scanned page
# carries only its text layer -- a page number, a header, often nothing -- on
# the order of 0-20 chars/page. 100 sits roughly 7x below real documents and 5x
# above a scan, so the margin is wide in both directions.
#
# Deliberately PDF-only. A 21-character .txt note is perfectly valid content;
# density is only meaningful when there are pages to divide by.
MIN_PDF_CHARS_PER_PAGE = 100


def extract_text(path: Path, file_type: FileType) -> str:
    if file_type is FileType.TXT:
        return _extract_txt(path)
    if file_type is FileType.PDF:
        return _extract_pdf(path)
    raise ValidationError(f"Unsupported file type: {file_type}")


def _extract_txt(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Real-world .txt files are not always UTF-8. Replacing undecodable
        # bytes keeps a mostly-readable document indexable rather than failing
        # the whole upload over one bad character.
        logger.warning("%s is not valid UTF-8; decoding with replacement", path.name)
        return raw.decode("utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as exc:
        # A malformed PDF is the caller's problem, not a server fault.
        raise ValidationError(f"Could not read PDF: {exc}") from exc

    return "\n\n".join(p for p in pages if p.strip())


def count_pdf_pages(path: Path) -> int:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        return len(PdfReader(str(path)).pages)
    except (PdfReadError, OSError, ValueError):
        return 0


def is_extraction_empty(text: str) -> bool:
    """Fully image-only PDFs extract to nothing at all.

    Indexing that produces zero chunks and a document that silently never
    appears in search results. Detecting it here turns a silent hole in the
    knowledge base into an explicit 422. OCR is out of scope.
    """
    return not text or not text.strip()


def is_pdf_text_too_sparse(text: str, page_count: int) -> bool:
    """A scanned PDF whose text layer holds only a page number or header.

    is_extraction_empty catches the fully-blank scan, but not the common one:
    real scans usually carry a thin text layer, so extraction returns something
    like "3". That is not empty, so it passed — the document was marked
    'indexed', reported chunk_count=1, and put a vector for "3" into the index
    where it could match a query and outrank a real answer. Worse, the user saw
    'indexed' and believed the file was searchable when none of its actual
    content was.

    Density separates the two cases cleanly: a real page carries hundreds of
    characters, a scanned one carries a handful. See MIN_PDF_CHARS_PER_PAGE.
    """
    if page_count <= 0:
        return False
    return len(text.strip()) / page_count < MIN_PDF_CHARS_PER_PAGE
