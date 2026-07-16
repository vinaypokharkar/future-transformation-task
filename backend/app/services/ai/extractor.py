import logging
from pathlib import Path

from app.core.exceptions import ValidationError
from app.models.document import FileType

logger = logging.getLogger(__name__)


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


def is_extraction_empty(text: str) -> bool:
    """Scanned and image-only PDFs extract to nothing.

    Indexing that produces zero chunks and a document that silently never
    appears in search results. Detecting it here turns a silent hole in the
    knowledge base into an explicit 422. OCR is out of scope.
    """
    return not text or not text.strip()
