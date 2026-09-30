"""PDF file processing and metadata extraction."""

import logging
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PdfMetadata(BaseModel):
    """Metadata extracted from a PDF document."""

    pages: int = Field(default=0, description="Total number of pages")
    title: str | None = Field(default=None, description="Document title")
    author: str | None = Field(default=None, description="Document author")
    subject: str | None = Field(default=None, description="Document subject")
    creator: str | None = Field(default=None, description="Software that created the document")
    producer: str | None = Field(default=None, description="Software that produced the PDF")
    error: str | None = Field(default=None, description="Error encountered if any")


def extract_pdf_text(file_path: str | Path) -> str:
    """Extract text from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text formatted with newline separators between pages.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("PDF file not found: %s", file_path)
        return f"Error extracting PDF: File not found: {file_path}"

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as dec_err:
                logger.warning("Could not decrypt PDF: %s", dec_err)

        text_parts: list[str] = []
        for idx, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text.strip())
            except Exception as page_err:
                logger.warning("Error extracting page %d from %s: %s", idx, file_path, page_err)

        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error("PDF extraction failed for %s: %s", file_path, e)
        return f"Error extracting PDF: {e}"


def get_pdf_metadata(file_path: str | Path) -> dict[str, Any]:
    """Retrieve metadata information from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Dictionary containing pages, title, author, subject, etc.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        meta = reader.metadata

        title = getattr(meta, "title", None) or (meta.get("/Title") if meta else None)
        author = getattr(meta, "author", None) or (meta.get("/Author") if meta else None)
        subject = getattr(meta, "subject", None) or (meta.get("/Subject") if meta else None)
        creator = getattr(meta, "creator", None) or (meta.get("/Creator") if meta else None)
        producer = getattr(meta, "producer", None) or (meta.get("/Producer") if meta else None)

        metadata_obj = PdfMetadata(
            pages=len(reader.pages),
            title=str(title) if title is not None else None,
            author=str(author) if author is not None else None,
            subject=str(subject) if subject is not None else None,
            creator=str(creator) if creator is not None else None,
            producer=str(producer) if producer is not None else None,
            error=None,
        )
        return {
            "pages": metadata_obj.pages,
            "title": metadata_obj.title,
            "author": metadata_obj.author,
            "subject": metadata_obj.subject,
            "creator": metadata_obj.creator,
            "producer": metadata_obj.producer,
        }
    except Exception as e:
        logger.error("Failed to read PDF metadata for %s: %s", file_path, e)
        return {"error": str(e)}
