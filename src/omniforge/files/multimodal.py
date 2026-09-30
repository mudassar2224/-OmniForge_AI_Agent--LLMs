"""Multimodal file routing and processing for various document and media formats."""

import json
import logging
import mimetypes
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from omniforge.files.pdf import extract_pdf_text, get_pdf_metadata
from omniforge.files.docx import extract_docx_text, get_docx_metadata
from omniforge.files.csv_handler import read_csv_file, analyze_csv
from omniforge.files.spreadsheet import read_spreadsheet, analyze_spreadsheet, get_sheet_names

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".svg"}
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".py",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".yaml",
    ".yml",
    ".xml",
    ".log",
    ".toml",
    ".ini",
    ".sh",
    ".bat",
    ".ps1",
    ".env",
    ".rst",
}


class ProcessedFileResult(BaseModel):
    """Normalized file processing result."""

    file_type: str = Field(description="Detected file category")
    path: str = Field(description="File system path")
    name: str = Field(description="Base file name")
    size_bytes: int = Field(default=0, description="File size in bytes")
    data: dict[str, Any] = Field(default_factory=dict, description="Extracted content and metadata")
    error: str | None = Field(default=None, description="Error message if processing encountered issues")


def get_file_type(file_path: str | Path) -> str:
    """Identify the file type based on extension and mime type.

    Args:
        file_path: Path to the file.

    Returns:
        One of 'pdf', 'docx', 'csv', 'xlsx', 'image', 'text', 'json', or 'unknown'.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return "pdf"
    if suffix in {".docx", ".doc"}:
        return "docx"
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return "xlsx"
    if suffix == ".json":
        return "json"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in TEXT_EXTENSIONS:
        return "text"

    # Mime type detection fallback
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        if mime == "application/pdf":
            return "pdf"
        if "wordprocessingml" in mime:
            return "docx"
        if mime == "text/csv":
            return "csv"
        if "spreadsheet" in mime or "excel" in mime:
            return "xlsx"
        if mime.startswith("image/"):
            return "image"
        if mime.startswith("text/"):
            return "text"
        if mime == "application/json":
            return "json"

    return "unknown"


def _process_image(path: Path) -> dict[str, Any]:
    """Extract metadata from an image file using PIL."""
    try:
        from PIL import Image

        with Image.open(path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
            }
    except Exception as e:
        logger.warning("Could not read image %s via PIL: %s", path, e)
        return {"error": str(e)}


def _process_json(path: Path) -> dict[str, Any]:
    """Parse JSON file and return structural summary."""
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys()),
                "num_keys": len(data),
                "preview": {k: data[k] for k in list(data.keys())[:10]},
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "preview": data[:5],
            }
        return {"type": type(data).__name__, "value": data}
    except Exception as e:
        logger.error("JSON parsing error for %s: %s", path, e)
        return {"error": str(e)}


def _process_text(path: Path) -> dict[str, Any]:
    """Read text file and report character and line statistics."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        return {
            "content": content,
            "line_count": len(lines),
            "char_count": len(content),
            "preview": lines[:20],
        }
    except Exception as e:
        logger.error("Text reading error for %s: %s", path, e)
        return {"error": str(e)}


def process_file(file_path: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Route a file to its appropriate extractor based on detected file type.

    Args:
        file_path: Path to the target file.
        **kwargs: Extra parameters passed to underlying handlers (e.g. nrows, sheet_name).

    Returns:
        Dictionary containing file_type, path, name, size_bytes, data, and error.
    """
    path = Path(file_path)
    if not path.exists():
        return ProcessedFileResult(
            file_type="unknown",
            path=str(path),
            name=path.name,
            size_bytes=0,
            data={},
            error=f"File not found: {file_path}",
        ).model_dump()

    size_bytes = path.stat().st_size
    file_type = get_file_type(path)
    data: dict[str, Any] = {}
    error: str | None = None

    try:
        if file_type == "pdf":
            text = extract_pdf_text(path)
            meta = get_pdf_metadata(path)
            data = {"text": text, "metadata": meta}

        elif file_type == "docx":
            text = extract_docx_text(path)
            meta = get_docx_metadata(path)
            data = {"text": text, "metadata": meta}

        elif file_type == "csv":
            nrows = kwargs.get("nrows", 10)
            read_res = read_csv_file(path, nrows=nrows)
            analysis_res = analyze_csv(path)
            data = {"preview": read_res, "analysis": analysis_res}

        elif file_type == "xlsx":
            sheet_name = kwargs.get("sheet_name", 0)
            nrows = kwargs.get("nrows", 10)
            read_res = read_spreadsheet(path, sheet_name=sheet_name, nrows=nrows)
            analysis_res = analyze_spreadsheet(path, sheet_name=sheet_name)
            data = {
                "sheet_names": get_sheet_names(path),
                "read": read_res,
                "analysis": analysis_res,
            }

        elif file_type == "image":
            data = _process_image(path)

        elif file_type == "json":
            data = _process_json(path)

        elif file_type == "text":
            data = _process_text(path)

        else:
            data = {
                "message": f"Unsupported or unknown file format '{path.suffix}'",
                "extension": path.suffix,
            }

    except Exception as e:
        logger.exception("Error processing file %s: %s", file_path, e)
        error = str(e)

    result = ProcessedFileResult(
        file_type=file_type,
        path=str(path),
        name=path.name,
        size_bytes=size_bytes,
        data=data,
        error=error,
    )
    return result.model_dump()
